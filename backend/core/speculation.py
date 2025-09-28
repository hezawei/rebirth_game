from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque, defaultdict
from datetime import datetime
from typing import Optional, Any, Callable

from sqlalchemy.exc import IntegrityError

from config.logging_config import LOGGER
from config.settings import settings
from database.base import SessionLocal
from database import crud
from database.models import StoryNode
from .story_engine import story_engine
from .story_state import build_story_history, extract_chapter_number
import threading


class SpeculationService:
    def __init__(self) -> None:
        self.enabled = settings.speculation_enabled
        self.max_depth = max(0, settings.speculation_max_depth)
        max_workers = max(1, settings.speculation_max_workers)
        self.level_cap = max(0, getattr(settings, 'speculation_level_cap', 0))
        self.choice_workers = max(1, getattr(settings, 'speculation_choice_workers', 3))
        self.executor: Optional[ThreadPoolExecutor] = None
        if self.enabled and self.max_depth > 0:
            LOGGER.info(
                f"[Speculation] enabled depth={self.max_depth} choice_workers={self.choice_workers} mode=thread-per-enqueue (no global pool)"
            )
        else:
            LOGGER.info("[Speculation] service disabled")

        # --- Metrics ---
        self._lock = threading.Lock()
        self.enqueued_total = 0
        self.started_total = 0
        self.finished_total = 0
        self.failed_total = 0
        self.active_workers = 0
        self.nodes_generated_total = 0
        self.nodes_failed_total = 0
        self.dropped_total = 0
        # 运行态跟踪：记录每个 (session_id, node_id) 的“最新请求深度”用于补齐窗口
        self._pending_jobs: dict[tuple[int, int], int] = {}  # (session_id, node_id) -> max requested depth
        self._user_active: dict[str, int] = {}
        # 流水线模式新增：追踪正在生成的任务
        self._generating_nodes: set[tuple[int, int, str]] = set()  # (session_id, parent_id, choice)
        # 图像并发优化：追踪正在进行图像生成的节点
        self._image_generating_nodes: set[int] = set()  # node_id

    def enqueue(self, session_id: int, node_id: int, depth: Optional[int] = None) -> None:
        """启动流水线式预推演：A节点完成后立即触发A的所有子节点生成"""
        if not self.enabled:
            return
        target_depth = depth if depth is not None else self.max_depth
        if target_depth <= 0:
            return
        LOGGER.debug(f"[Speculation] enqueue PIPELINE session={session_id} node={node_id} depth={target_depth}")
        with self._lock:
            key = (session_id, node_id)
            if key in self._pending_jobs:
                # 若任务已在进行，仅抬升其期望深度（取较大值）；不重复启动线程
                prev = self._pending_jobs[key]
                if target_depth > prev:
                    self._pending_jobs[key] = target_depth
                    LOGGER.debug(f"[Speculation] raise pending depth session={session_id} node={node_id} {prev} -> {target_depth}")
                else:
                    LOGGER.debug(f"[Speculation] duplicate enqueue ignored session={session_id} node={node_id} depth={target_depth} (pending={prev})")
                return
            # 新任务：登记请求深度并启动线程
            self._pending_jobs[key] = target_depth
            self.enqueued_total += 1
        threading.Thread(target=self._run_pipeline, args=(session_id, node_id, target_depth), daemon=True).start()
    
    def is_choice_generating(self, session_id: int, parent_id: int, choice: str) -> bool:
        """检查某个选项是否正在生成中（竞态保护）"""
        with self._lock:
            return (session_id, parent_id, choice) in self._generating_nodes
    
    def is_node_image_generating(self, node_id: int) -> bool:
        """检查某个节点是否正在进行图像生成（竞态保护）"""
        with self._lock:
            return node_id in self._image_generating_nodes

    # --- internal helpers ---

    def _run_pipeline(self, session_id: int, node_id: int, depth: int) -> None:
        """流水线模式：为指定节点启动其所有子选项的并发生成"""
        db = SessionLocal()
        with self._lock:
            self.started_total += 1
            self.active_workers += 1
        try:
            # 基于用户的并发限制：超过限制则丢弃本次任务
            session = crud.get_session_by_id(db, session_id)
            user_id = getattr(session, 'user_id', None) if session else None
            limit = max(0, getattr(settings, 'speculation_max_concurrency_per_user', 0))
            if user_id and limit > 0:
                with self._lock:
                    cur = self._user_active.get(str(user_id), 0)
                    if cur >= limit:
                        LOGGER.info(f"[Speculation] drop job due to per-user concurrency limit user={user_id} session={session_id} node={node_id}")
                        self.dropped_total += 1
                        return
                    self._user_active[str(user_id)] = cur + 1

            # 轮询：若执行期间外界抬升了目标深度，则在本轮完成后继续补齐
            while True:
                with self._lock:
                    key = (session_id, node_id)
                    requested = self._pending_jobs.get(key, depth)
                # 为当前节点生成所有子节点，完成后为每个子节点递归触发，直到 requested 深度
                self._generate_children_pipeline(db, session, node_id, requested)
                # 检查是否需要进一步加深（在本轮执行期间被抬升）
                with self._lock:
                    latest = self._pending_jobs.get(key, 0)
                    if latest > requested:
                        LOGGER.debug(f"[Speculation] depth top-up detected session={session_id} node={node_id} {requested} -> {latest}")
                        continue
                    # 无更大需求，清理 pending 并退出
                    if key in self._pending_jobs:
                        self._pending_jobs.pop(key, None)
                    break
        except Exception as exc:  # noqa: BLE001
            LOGGER.error(
                f"[Speculation] pipeline failed session={session_id} node={node_id} depth={depth}: {exc}",
                exc_info=True,
            )
            with self._lock:
                self.failed_total += 1
        finally:
            with self._lock:
                self.finished_total += 1
                self.active_workers = max(0, self.active_workers - 1)
                # pending 标记在执行循环内根据需要清理
            # 减少用户活跃计数
            try:
                if session and getattr(session, 'user_id', None):
                    uid = str(session.user_id)
                    with self._lock:
                        if uid in self._user_active:
                            self._user_active[uid] = max(0, self._user_active[uid] - 1)
                            if self._user_active[uid] == 0:
                                self._user_active.pop(uid, None)
            except Exception:
                pass
            db.close()

    def _run(self, session_id: int, node_id: int, depth: int) -> None:
        """旧版BFS模式（保留用于兼容）"""
        return self._run_pipeline(session_id, node_id, depth)

    def _generate_children_pipeline(self, db: Any, session: Any, parent_node_id: int, remaining_depth: int) -> None:
        """
        流水线模式的核心：为父节点的所有选项并发生成子节点，
        每个子节点完成后立即递归触发其下一层的生成。
        """
        # depth semantics: remaining_depth==1 still generates one layer; stop only when <=0
        if remaining_depth <= 0:
            return  # 无需继续扩展

        parent_node: Optional[StoryNode] = crud.get_node_by_id(db, parent_node_id)
        if not parent_node:
            return

        # Do not cleanup speculative children; keep caches for reuse
        db.refresh(parent_node)

        choices = parent_node.get_choices()
        if not choices:
            LOGGER.debug(f"[Speculation] node={parent_node_id} has no choices; pipeline ends")
            return

        history = build_story_history(db, parent_node)
        existing_children = {child.user_choice: child for child in parent_node.children}
        
        # Disable expiry: keep speculative nodes indefinitely for reuse
        expiry_at = None

        # 收集需要生成的选项
        tasks_to_run = []
        for choice_payload in choices:
            choice_text = choice_payload.get("option") or choice_payload.get("text")
            if not choice_text:
                continue
            
            # 检查是否已存在
            if choice_text in existing_children:
                child = existing_children[choice_text]
                if child and remaining_depth > 1:
                    self.enqueue(session.id, child.id, remaining_depth - 1)
                continue
            
            # 检查是否正在生成中（竞态保护）
            if self.is_choice_generating(session.id, parent_node_id, choice_text):
                LOGGER.debug(f"[Speculation] choice '{choice_text}' already generating, skip")
                continue
                
            # 添加到并发任务队列
            tasks_to_run.append((choice_text, parent_node, history, expiry_at, remaining_depth))

        if not tasks_to_run:
            LOGGER.debug(f"[Speculation] no new choices to generate for node={parent_node_id}")
            return

        # 标记正在生成的任务
        with self._lock:
            for choice_text, *_ in tasks_to_run:
                self._generating_nodes.add((session.id, parent_node_id, choice_text))

        LOGGER.debug(f"[Speculation] pipeline generating {len(tasks_to_run)} children for node={parent_node_id}")
        
        # 并发生成所有新子节点
        with ThreadPoolExecutor(max_workers=self.choice_workers, thread_name_prefix="pipeline_choice") as executor:
            future_to_task = {}
            for choice_text, parent_node, history, expiry_at, next_depth in tasks_to_run:
                future = executor.submit(self._generate_child_node, db, session, parent_node, choice_text, history, expiry_at)
                future_to_task[future] = (choice_text, next_depth)

            # 收集结果，对于每个成功的子节点立即触发下一层
            for future in as_completed(future_to_task):
                choice_text, next_depth = future_to_task[future]
                try:
                    child_node = future.result()
                    if child_node and next_depth > 1:
                        # 每个子节点完成后立即触发其下一层生成（流水线）
                        self.enqueue(session.id, child_node.id, next_depth - 1)
                        LOGGER.debug(f"[Speculation] child node={child_node.id} completed, triggered next level depth={next_depth-1}")
                except Exception as exc:
                    LOGGER.error(f"[Speculation] pipeline child generation failed for choice '{choice_text}': {exc}")
                finally:
                    # 清理生成中标记
                    with self._lock:
                        self._generating_nodes.discard((session.id, parent_node_id, choice_text))

    def _generate_child_node(self, db: Any, session: Any, parent_node: StoryNode, choice_text: str, history: list, expiry_at: Optional[datetime]) -> Optional[StoryNode]:
        """为单个选项生成子节点的独立任务单元（故事+图像串行块）"""

        def _compact(text: str, limit: int = 400) -> str:
            single_line = " ".join(text.split())
            return single_line if len(single_line) <= limit else f"{single_line[:limit]}…"

        LOGGER.info(
            f"[Speculation] start | parent={parent_node.id} | choice=\"{choice_text}\""
        )

        try:
            chapter_number = extract_chapter_number(parent_node)
            base_success_rate = parent_node.success_rate if parent_node.success_rate is not None else 50

            raw = story_engine.continue_story(
                wish=session.wish,
                story_history=history,
                choice=choice_text,
                chapter_number=chapter_number,
                current_success_rate=base_success_rate,
                parent_metadata=parent_node.get_metadata(),
            )
            LOGGER.info(
                f"[Speculation] story | parent={parent_node.id} | choice=\"{choice_text}\" | text_len={len(raw.text)} | text=\"{_compact(raw.text, 2000)}\""
            )

        except Exception as exc:
            LOGGER.warning(
                f"[Speculation] story_failed | parent={parent_node.id} | choice=\"{choice_text}\" | error={exc}"
            )
            with self._lock:
                self.nodes_failed_total += 1
            return None

        try:
            child = crud.create_story_node(
                db,
                session_id=session.id,
                segment=raw,
                parent_id=parent_node.id,
                user_choice=choice_text,
                is_speculative=True,
                speculative_depth=(parent_node.speculative_depth or self.max_depth) - 1,
            )

        except IntegrityError:
            db.rollback()
            child = crud.get_child_by_parent_and_choice(db, session.id, parent_node.id, choice_text)
            if not child:
                LOGGER.error(
                    f"[Speculation] node_missing | parent={parent_node.id} | choice=\"{choice_text}\""
                )
                return None
        except Exception as exc:
            LOGGER.error(
                f"[Speculation] node_failed | parent={parent_node.id} | choice=\"{choice_text}\" | error={exc}"
            )
            db.rollback()
            return None

        LOGGER.info(
            f"[Speculation] complete | parent={parent_node.id} | choice=\"{choice_text}\" | node={child.id} | text_len={len(raw.text)} | image={child.image_url}"
        )

        with self._lock:
            self.nodes_generated_total += 1
        return child

    def _speculate_bfs(self, db: Any, session_id: int, root_node_id: int, depth: int) -> None:
        """按层（BFS）并发预推演"""
        if depth <= 0: return
        session = crud.get_session_by_id(db, session_id)
        if not session: return

        # Disable expiry in BFS fallback as well
        expiry_at = None
        level_cap = max(0, self.level_cap)
        choice_workers = max(1, getattr(settings, 'speculation_choice_workers', 1))

        q = deque([(root_node_id, depth, 0)])
        visited = {root_node_id}

        while q:
            node_id, remaining, level = q.popleft()
            if remaining <= 0: continue

            node: Optional[StoryNode] = crud.get_node_by_id(db, node_id)
            if not node: continue

            # Do not cleanup caches
            db.refresh(node)

            choices = node.get_choices()
            if not choices: continue

            history = build_story_history(db, node)
            existing_children = {child.user_choice: child for child in node.children}
            tasks_to_run: list[tuple[Callable, list[Any]]] = []

            created_this_level = 0

            for choice_payload in choices:
                choice_text = choice_payload.get("option") or choice_payload.get("text")
                if not choice_text: continue

                if choice_text in existing_children:
                    child = existing_children[choice_text]
                    if child and (remaining - 1) > 0 and child.id not in visited:
                        q.append((child.id, remaining - 1, level + 1))
                        visited.add(child.id)
                else:
                    if level_cap > 0 and created_this_level >= level_cap:
                        continue
                    tasks_to_run.append((self._generate_child_node, [db, session, node, choice_text, history, expiry_at]))
                    created_this_level += 1
            
            if not tasks_to_run: continue

            with ThreadPoolExecutor(max_workers=choice_workers, thread_name_prefix="spec_choice") as executor:
                futures = {executor.submit(func, *args): (func, args) for func, args in tasks_to_run}
                for future in as_completed(futures):
                    try:
                        child_node = future.result()
                        if child_node and (remaining - 1) > 0 and child_node.id not in visited:
                            q.append((child_node.id, remaining - 1, level + 1))
                            visited.add(child_node.id)
                    except Exception as exc:
                        func, args = futures[future]
                        LOGGER.error(f"[Speculation] future failed for {func.__name__} with args {args[:4]}: {exc}")


speculation_service = SpeculationService()


def _safe_int(v: Optional[int]) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


def _safe_bool(v) -> bool:
    return bool(v)


def _safe_str(v) -> Optional[str]:
    return str(v) if v is not None else None


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


def speculation_get_metrics() -> dict:
    svc = speculation_service
    with svc._lock:
        return {
            "enabled": _safe_bool(svc.enabled),
            "max_depth": _safe_int(svc.max_depth),
            "active_workers": _safe_int(svc.active_workers),
            "enqueued_total": _safe_int(svc.enqueued_total),
            "started_total": _safe_int(svc.started_total),
            "finished_total": _safe_int(svc.finished_total),
            "failed_total": _safe_int(svc.failed_total),
            "nodes_generated_total": _safe_int(svc.nodes_generated_total),
            "nodes_failed_total": _safe_int(svc.nodes_failed_total),
            "dropped_total": _safe_int(svc.dropped_total),
            "pending_jobs": len(svc._pending_jobs),
            "timestamp": _utcnow_iso(),
        }
