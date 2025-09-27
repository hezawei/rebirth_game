"""
故事相关的API端点
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Optional, Tuple, Any
# 【核心修正】导入整个schemas模块，而不仅仅是其中的类
from backend import schemas
from core.story_engine import story_engine
from core.history_context import build_prompt_context
from config.logging_config import LOGGER
from config.settings import settings
from database.base import get_db, SessionLocal
from database import crud, models
# 导入新的安全依赖
from .user import get_current_user
from core.content_moderation import check_wish_safety_llm
from core.prompt_templates import PREPARE_LEVEL_PROMPT
from core.llm_clients import llm_client
from core.story_state import build_story_history, extract_chapter_number, build_story_segment_from_node
from core.speculation import speculation_service, speculation_get_metrics
import json
import re
import threading

SAVE_STATUSES = {"active", "completed", "failed"}


def _ensure_session_ownership(session: models.GameSession, user_id: str) -> None:
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该游戏会话")


def _ensure_node_belongs_to_session(node: models.StoryNode, session_id: int) -> None:
    if not node or node.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在或不属于该会话")


def _build_save_detail(db: Session, save: models.StorySave) -> schemas.story.StorySaveDetail:
    segment = build_story_segment_from_node(db, save.node, source="save")
    # 防止泄露内部字段
    try:
        segment = segment.model_copy(update={"metadata": _sanitize_metadata(segment.metadata)})
    except Exception:
        pass
    return schemas.story.StorySaveDetail(
        id=save.id,
        session_id=save.session_id,
        node_id=save.node_id,
        title=save.title,
        status=save.status,
        created_at=save.created_at,
        updated_at=save.updated_at,
        node=segment,
    )

# 创建路由器
router = APIRouter()

# 简化的第一节故事预生成缓存
_FIRST_STORY_CACHE: Dict[str, Any] = {}  # key: f"{user_id}:{wish_hash}"
_CACHE_LOCK = threading.Lock()


def _background_generate_with_pregeneration(user_id: str, wish: str) -> None:
    """后台生成第一节故事并创建完整数据库记录，触发预生成"""
    db = SessionLocal()
    try:
        LOGGER.info(f"[预生成] 开始完整故事生成流程: user={user_id}")
        
        # 1. 生成第一节故事
        LOGGER.info(f"[预生成] 调用story_engine.start_story开始: user={user_id}")
        raw_data = story_engine.start_story(wish=wish)
        LOGGER.info(f"[预生成] 第一节故事LLM生成完成: user={user_id}, text长度={len(raw_data.text)}")
        
        # 2. 创建游戏会话
        session = crud.create_game_session(db, wish=wish.strip(), user_id=user_id)
        LOGGER.info(f"[预生成] 创建会话成功: session_id={session.id}")
        
        # 3. 创建第一个故事节点
        node = crud.create_story_node(db, session_id=session.id, segment=raw_data)
        LOGGER.info(f"[预生成] 创建第一个节点成功: node_id={node.id}")
        
        # 注意：raw_data.image_url 已经通过 story_engine 处理过图像逻辑了
        LOGGER.info(f"[预生成] 首节点图像已由story_engine处理: node_id={node.id} image_url={raw_data.image_url}")
        
        # 4. 缓存会话和节点信息供start接口使用
        cache_key = f"{user_id}:{hash(wish)}"
        with _CACHE_LOCK:
            _FIRST_STORY_CACHE[cache_key] = {
                "session_id": session.id,
                "node_id": node.id
            }
        
        # 5. 触发预生成：第一节相对概要已占1层，这里只需补齐到 max_depth，因此使用 (max_depth - 1)
        pre_depth = max(0, int(getattr(settings, 'speculation_max_depth', 0)) - 1)
        speculation_service.enqueue(session.id, node.id, depth=pre_depth)
        LOGGER.info(f"[预生成] 已触发speculation预生成: session={session.id}, node={node.id}")
        
        LOGGER.info(f"[预生成] 完整流程成功完成: user={user_id}, session={session.id}")
        
    except Exception as exc:
        LOGGER.error(f"[预生成] 完整流程失败: user={user_id}, error={exc}")
        db.rollback()
        # 失败时清理缓存，让start接口降级到实时生成
        cache_key = f"{user_id}:{hash(wish)}"
        with _CACHE_LOCK:
            _FIRST_STORY_CACHE.pop(cache_key, None)
    finally:
        # 无论成功失败都确保关闭数据库会话
        db.close()
        LOGGER.debug(f"[预生成] 数据库会话已安全关闭: user={user_id}")



def _wait_for_node_complete(node, db, max_wait_seconds: int = 60) -> bool:
    """
    等待节点完全准备就绪（故事+图片都完成）
    只有用户明确选择了该节点时才会调用此方法
    """
    import time
    from pathlib import Path
    
    LOGGER.info(f"[NodeComplete] 开始等待节点完全准备：node_id={node.id}")
    
    start_time = time.time()
    check_interval = 0.5  # 500ms检查一次
    
    while time.time() - start_time < max_wait_seconds:
        # 刷新节点状态
        db.refresh(node)
        
        # 检查1: 故事文本是否存在
        if not node.story_text or len(node.story_text.strip()) == 0:
            LOGGER.debug(f"[NodeComplete] 故事文本未完成，继续等待：node_id={node.id}")
            time.sleep(check_interval)
            continue
        
        # 检查2: 图片URL是否存在
        if not node.image_url:
            LOGGER.debug(f"[NodeComplete] 图片URL未设置，继续等待：node_id={node.id}")
            time.sleep(check_interval)
            continue
        
        # 检查3: 如果是AI生成的图片，检查文件是否真的存在且可访问
        if node.image_url.startswith('/static/generated/'):
            # 这是AI生成的图片，需要验证文件存在性
            filename = node.image_url.replace('/static/generated/', '')
            file_path = settings.BASE_DIR / "assets" / "generated_images" / filename
            
            if not file_path.exists():
                LOGGER.debug(f"[NodeComplete] AI生成图片文件不存在，继续等待：{file_path}")
                time.sleep(check_interval)
                continue
            
            # 检查文件大小
            if file_path.stat().st_size == 0:
                LOGGER.debug(f"[NodeComplete] AI生成图片文件为空，继续等待：{file_path}")
                time.sleep(check_interval)
                continue
            
            # 尝试读取文件头确保文件完整
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(10)
                    if len(header) == 0:
                        LOGGER.debug(f"[NodeComplete] AI生成图片文件无法读取，继续等待：{file_path}")
                        time.sleep(check_interval)
                        continue
            except Exception as e:
                LOGGER.debug(f"[NodeComplete] AI生成图片文件访问异常，继续等待：{e}")
                time.sleep(check_interval)
                continue
        
        # 所有检查都通过
        elapsed = time.time() - start_time
        LOGGER.info(f"[NodeComplete] ✅ 节点完全准备就绪：node_id={node.id} (等待了 {elapsed:.1f} 秒)")
        return True
    
    # 超时
    elapsed = time.time() - start_time
    LOGGER.warning(f"[NodeComplete] ⏰ 节点准备等待超时：node_id={node.id} (等待了 {elapsed:.1f} 秒)")
    return False


def _sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """去除只供后端使用的敏感/内部字段，避免泄露到前端。
    当前仅移除 chapter.hidden_effects_map，但保留 chapter.enabled 等前端需要的标识。
    """
    if not isinstance(meta, dict):
        return meta
    clean = dict(meta)
    chapter = clean.get("chapter")
    if isinstance(chapter, dict):
        chapter_clean = dict(chapter)
        # 移除敏感字段
        if "hidden_effects_map" in chapter_clean:
            chapter_clean.pop("hidden_effects_map", None)
        # 保留前端需要的标识
        chapter_clean["hide_success_rate"] = True  # 告诉前端隐藏成功率显示
        clean["chapter"] = chapter_clean
    return clean


@router.post("/check_wish", response_model=schemas.story.WishCheckResponse)
async def check_wish(
    request: schemas.story.WishCheckRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """使用LLM校验用户的重生愿望是否违规"""
    text = (request.wish or "").strip()
    
    # 基本长度校验
    if not text or len(text) > 100:
        reason = "愿望不能为空且不超过100字"
        try:
            crud.log_wish_moderation(db, current_user.id, text, "rejected", reason)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(f"[moderation] log wish failed: {exc}")
        return schemas.story.WishCheckResponse(ok=False, reason=reason)

    # 直接使用LLM校验
    try:
        ok, reason = check_wish_safety_llm(text)
        status = "accepted" if ok else "rejected"
        
        try:
            crud.log_wish_moderation(db, current_user.id, text, status, reason)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(f"[moderation] log wish failed: {exc}")
            
        LOGGER.info(f"[moderation] LLM校验 user={current_user.id} ok={ok} reason={reason or '-'}")
        
        if not ok:
            return schemas.story.WishCheckResponse(ok=False, reason=reason or "愿望内容不合适")
        
        return schemas.story.WishCheckResponse(ok=True)
        
    except Exception as exc:  # noqa: BLE001
        LOGGER.error(f"[moderation] LLM校验失败 user={current_user.id}: {exc}")
        # 校验失败时保守处理
        try:
            crud.log_wish_moderation(db, current_user.id, text, "rejected", "系统校验失败")
        except Exception:
            pass
        return schemas.story.WishCheckResponse(ok=False, reason="愿望校验失败，请稍后重试")


@router.post("/prepare_start", response_model=schemas.story.PrepareStartResponse)
async def prepare_start_level(
    request: schemas.story.PrepareStartRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    根据愿望生成第一关的关卡元信息（不创建会话）
    假设愿望已通过校验，直接生成故事概要。
    """
    # 故事概要生成（这是耗时操作，应该在校验之后单独调用）
    LOGGER.info(f"[PrepareStart] 🚀 开始生成故事概要，愿望：{request.wish.strip()[:50]}...")

    LOGGER.debug("[PrepareStart] 构建提示词上下文...")
    prompt_context = build_prompt_context(request.wish.strip())
    LOGGER.debug(f"[PrepareStart] 上下文构建完成，推荐章节数: {prompt_context.get('recommended_chapter_count', 'N/A')}")
    
    tpl = PREPARE_LEVEL_PROMPT
    prompt = tpl.format(
        wish=request.wish.strip(),
        history_context=prompt_context["context_block"],
    )
    LOGGER.info(f"[PrepareStart] 📝 调用LLM生成关卡元信息，提示词长度: {len(prompt)}")
    raw = llm_client.generate(prompt)
    LOGGER.info(f"[PrepareStart] ✅ LLM响应完成，响应长度: {len(str(raw))}")
    try:
        s = str(raw).strip()
        # 兼容 ```json 代码围栏
        m = re.match(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", s, re.IGNORECASE | re.DOTALL)
        if m:
            s = m.group(1).strip()
        else:
            # 兼容前后噪声：从首个 '{' 起按括号配对截取
            start = s.find('{')
            if start != -1:
                depth = 0
                end = None
                for i in range(start, len(s)):
                    ch = s[i]
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                if end is not None:
                    s = s[start:end+1].strip()
                else:
                    s = s[start:].strip()
        data = json.loads(s)
        LOGGER.info(f"[PrepareStart] 📊 JSON解析成功，包含字段: {list(data.keys())}")
    except Exception as e:
        LOGGER.error(f"[PrepareStart] ❌ 解析关卡元信息失败: {e}; 原始响应: {str(raw)[:200]}...")
        raise HTTPException(status_code=500, detail="生成关卡元信息失败，请稍后重试")

    level_title = data.get("level_title")
    background = data.get("background")
    # V2: 从 goal.description 映射 main_quest
    main_quest = data.get("main_quest")
    if not main_quest and isinstance(data.get("goal"), dict):
        main_quest = data["goal"].get("description")
    
    LOGGER.debug(f"[PrepareStart] 解析结果 - title: {level_title}, background: {background[:50] if background else None}..., quest: {main_quest[:50] if main_quest else None}...")
    
    if not all([level_title, background, main_quest]):
        LOGGER.error(f"[PrepareStart] ❌ 关卡元信息缺失字段: {data}")
        raise HTTPException(status_code=500, detail="生成关卡元信息不完整，请稍后重试")

    meta = {
        "wish": request.wish.strip(),
        "history_profile": prompt_context["profile_dict"],
        "recommended_chapter_count": prompt_context["recommended_chapter_count"],
        "anchor_events": prompt_context["anchor_events"],
    }
    # 返回阈值以便前端展示目标说明（不敏感）
    meta.update({
        "prepare": {
            "goal": data.get("goal"),
            "min_nodes": data.get("min_nodes"),
            "max_nodes": data.get("max_nodes"),
            "pass_threshold": data.get("pass_threshold"),
            "fail_threshold": data.get("fail_threshold"),
        }
        })

    # 触发后台完整故事生成流程（包含session创建和speculation预生成）
    wish_norm = request.wish.strip()
    try:
        thread = threading.Thread(
            target=_background_generate_with_pregeneration,
            args=(str(current_user.id), wish_norm),
            daemon=True
        )
        thread.start()
        LOGGER.info(f"[预生成] 已启动后台完整故事生成线程: user={current_user.id}")
    except Exception as exc:
        LOGGER.warning(f"[预生成] 启动后台生成失败: {exc}")

    return schemas.story.PrepareStartResponse(
        level_title=level_title,
        background=background,
        main_quest=main_quest,
        metadata=meta
    )


@router.post("/start", response_model=schemas.story.StorySegment)
async def start_new_story(
    request: schemas.story.StoryStartRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    开始新的重生故事 (需要认证)

    Args:
        request: 包含用户重生愿望的请求
        db: 数据库会话
        current_user: 从JWT获取的当前用户模型

    Returns:
        StorySegment: 包含故事文本、选择选项和图片的响应
    """

    user_id = current_user.id
    LOGGER.info(f"[Start] 👤 用户 {user_id} 收到新故事请求，愿望: {request.wish[:50]}...")

    # 基本验证（愿望应该已通过check_wish校验）
    LOGGER.debug(f"[Start] 愿望校验已通过，开始处理故事生成")

    # 优先使用预生成的session和node，否则降级到实时生成
    wish_norm = request.wish.strip()
    cache_key = f"{user_id}:{hash(wish_norm)}"
    LOGGER.debug(f"[Start] 生成缓存键: {cache_key}")
    
    cached_data = None
    cache_wait_seconds = getattr(settings, "start_cache_wait_seconds", 8)
    poll_interval = 0.4
    elapsed = 0.0

    with _CACHE_LOCK:
        cached_data = _FIRST_STORY_CACHE.pop(cache_key, None)
        LOGGER.info(f"[Start] 🔍 缓存查询结果: {'命中' if cached_data else '未命中'} (初始)")

    while cached_data is None and elapsed < cache_wait_seconds:
        remaining = cache_wait_seconds - elapsed
        wait = poll_interval if remaining > poll_interval else remaining
        LOGGER.info(f"[Start] ⏳ 缓存未就绪，等待 {wait:.1f}s 后重试 (已等待 {elapsed:.1f}s / {cache_wait_seconds}s)")
        threading.Event().wait(wait)
        elapsed += wait
        with _CACHE_LOCK:
            cached_data = _FIRST_STORY_CACHE.pop(cache_key, None)
            if cached_data:
                LOGGER.info(f"[Start] 🔁 等待后命中缓存: session={cached_data['session_id']}, node={cached_data['node_id']}, 总等待 {elapsed:.1f}s")

    if cached_data is not None:
        # 使用预生成的session和node
        session_id = cached_data["session_id"]
        node_id = cached_data["node_id"]
        LOGGER.info(f"[预生成] 命中缓存，使用预生成的会话和节点: session={session_id}, node={node_id}")
        
        session = crud.get_session_by_id(db, session_id)
        node = crud.get_node_by_id(db, node_id)
        
        if not session or not node:
            LOGGER.warning(f"[Start] ⚠️ 缓存的会话或节点不存在，降级到实时生成: session={bool(session)}, node={bool(node)}")
            # 降级到实时生成
            LOGGER.info(f"[Start] 🏗️ 创建新游戏会话...")
            session = crud.create_game_session(db, wish=wish_norm, user_id=user_id)
            LOGGER.info(f"[Start] ✅ 会话创建完成: session_id={session.id}")
            
            LOGGER.info(f"[Start] 🎲 调用故事引擎生成第一节故事...")
            raw_data = story_engine.start_story(wish=wish_norm)
            LOGGER.info(f"[Start] 📖 第一节故事生成完成，文本长度: {len(raw_data.text)}")
            
            LOGGER.info(f"[Start] 💾 保存第一节故事到数据库...")
            node = crud.create_story_node(db, session_id=session.id, segment=raw_data)
            LOGGER.info(f"[Start] ✅ 节点创建完成: node_id={node.id}")
        else:
            # 使用预生成的节点，无需raw_data
            LOGGER.info(f"[Start] ✅ 使用预生成节点: session_id={session.id}, node_id={node.id}")
            raw_data = None
    else:
        LOGGER.info(f"[Start] 🔄 未命中缓存，实时生成第一节故事: user={user_id}")
        # 降级到实时生成
        LOGGER.info(f"[Start] 🏗️ 创建新游戏会话...")
        session = crud.create_game_session(db, wish=wish_norm, user_id=user_id)
        LOGGER.info(f"[Start] ✅ 会话创建完成: session_id={session.id}")
        
        LOGGER.info(f"[Start] 🎲 调用故事引擎生成第一节故事...")
        raw_data = story_engine.start_story(wish=wish_norm)
        LOGGER.info(f"[Start] 📖 第一节故事生成完成，文本长度: {len(raw_data.text)}")
        
        LOGGER.info(f"[Start] 💾 保存第一节故事到数据库...")
        node = crud.create_story_node(db, session_id=session.id, segment=raw_data)
        LOGGER.info(f"[Start] ✅ 节点创建完成: node_id={node.id}")

    # 4. 【逻辑简化】开始故事永远是第1章
    chapter_number = 1

    # 5. 组合最终响应
    # 【核心修改】确保 metadata 结构一致
    if raw_data is not None:
        # 实时生成的情况，使用raw_data
        metadata = {
            **(raw_data.metadata or {}),
            "chapter_number": chapter_number
        }
        choices_payload = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in (raw_data.choices or [])
        ]
        story_text = raw_data.text
        image_url = raw_data.image_url
        success_rate = raw_data.success_rate
    else:
        # 使用预生成节点的情况，从node获取数据
        metadata = {
            **(node.get_metadata() or {}),
            "chapter_number": chapter_number
        }
        choices_payload = node.get_choices() or []
        story_text = node.story_text  # 修正：使用正确的属性名
        image_url = node.image_url
        success_rate = node.success_rate
    
    result = schemas.story.StorySegment(
        session_id=session.id,
        node_id=node.id,
        text=story_text,
        choices=choices_payload,
        image_url=image_url,
        success_rate=success_rate,
        metadata=_sanitize_metadata(metadata),
    )

    LOGGER.info(f"[Start] 🎉 新故事生成成功！session_id={result.session_id}, node_id={result.node_id}")
    LOGGER.info(f"[Start] 📊 响应详情 - 文本长度: {len(result.text)}, 选择数: {len(result.choices or [])}, 图片: {result.image_url}")
    LOGGER.info(f"[Start] 🖼️ [图片URL调试] 返回给前端的图片URL: {result.image_url}")
    # 【调试】检查图片文件是否真实存在
    if result.image_url and '/static/generated/' in result.image_url:
        filename = result.image_url.split('/')[-1]
        local_file_path = settings.BASE_DIR / "assets" / "generated_images" / filename
        file_exists = local_file_path.exists()
        file_size = local_file_path.stat().st_size if file_exists else 0
        LOGGER.info(
            f"[Start] 📁 [图片文件检查] 文件存在: {file_exists}, 大小: {file_size}字节, 路径: {local_file_path}"
        )

    # 动态窗口：无论是否命中预生成，都要从“当前节点=第一节”补齐到 max_depth 层
    LOGGER.info(f"[Start] 🔮 触发动态窗口补齐: session={session.id}, node={node.id}, depth={settings.speculation_max_depth}")
    speculation_service.enqueue(session.id, node.id, depth=settings.speculation_max_depth)
    LOGGER.info(f"[Start] ✅ speculation补齐任务已启动")

    LOGGER.info(f"[Start] 🚀 API响应即将返回，图片URL: {result.image_url}")
    return result


@router.post("/continue", response_model=schemas.story.StorySegment)
async def continue_existing_story(
    request: schemas.story.StoryContinueRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    继续现有故事

    Args:
        request: 包含session_id、node_id和用户选择的请求
        db: 数据库会话

    Returns:
        StorySegment: 包含新故事文本、选择选项和图片的响应
    """
    LOGGER.info(f"收到故事继续请求，选择: {request.choice}")

    # 验证输入
    if not request.choice or len(request.choice.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户选择不能为空"
        )

    # 0. 权限与归属校验
    session = crud.get_session_by_id(db, request.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该游戏会话")

    # 校验节点是否属于该会话
    parent_node = crud.get_node_by_id(db, request.node_id)
    if not parent_node or parent_node.session_id != request.session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在或不属于该会话")

    # 1. 构建从根到当前父节点的路径历史
    story_history = build_story_history(db, parent_node)
    parent_chapter = extract_chapter_number(parent_node)
    current_success_rate = parent_node.success_rate
    
    # success_rate可能为None（隐藏数值），这是正常的

    # 竞态保护：如果该选项正在生成中，等待其完成（对用户无感）
    wait_interval = 0.3
    while speculation_service.is_choice_generating(request.session_id, request.node_id, request.choice.strip()):
        import time
        time.sleep(wait_interval)

    # 动态窗口：不做过期清理，保留可复用的预推演缓存

    # 2. 幂等性检查：是否已经存在同父节点、同选择的子节点（处理双击/并发重放）
    existing_child = crud.get_child_by_parent_and_choice(
        db, request.session_id, request.node_id, request.choice.strip()
    )
    if existing_child:
        if existing_child.is_speculative:
            existing_child = crud.finalize_speculative_node(db, existing_child)
        
        # 【节点完整性检查】确保用户选择的节点(故事+图片)都完全准备好了
        LOGGER.info(f"[NodeReady] 检查节点完整性：node_id={existing_child.id}")
        
        if _wait_for_node_complete(existing_child, db):
            LOGGER.info(f"[NodeReady] ✅ 节点完全准备就绪：node_id={existing_child.id}")
        else:
            LOGGER.warning(f"[NodeReady] ⚠️ 节点准备超时，但继续返回：node_id={existing_child.id}")
        
        chapter_number = crud.calculate_chapter_number(db, request.session_id, existing_child.id)
        metadata = existing_child.get_metadata() or {}
        metadata.update({"source": "continue", "chapter_number": chapter_number})
        metadata = _sanitize_metadata(metadata)
        # 补齐以“当前节点=已选择的子节点”为锚的 max_depth 窗口
        LOGGER.info(f"[Continue] 🔮 触发动态窗口补齐(已存在子节点): session={request.session_id}, node={existing_child.id}, depth={settings.speculation_max_depth}")
        speculation_service.enqueue(request.session_id, existing_child.id, depth=settings.speculation_max_depth)
        return schemas.story.StorySegment(
            session_id=request.session_id,
            node_id=existing_child.id,
            text=existing_child.story_text,
            choices=existing_child.get_choices(),
            image_url=existing_child.image_url,
            success_rate=existing_child.success_rate,
            metadata=metadata,
        )

    # 2b. 调用引擎生成下一段故事 (返回RawStoryData) — 在事务之外执行，避免长事务
    raw_data = story_engine.continue_story(
        wish=session.wish,
        story_history=story_history,
        choice=request.choice.strip(),
        chapter_number=parent_chapter,
        current_success_rate=current_success_rate,
        parent_metadata=parent_node.get_metadata(),
    )

    # 3. 创建新的故事节点（短事务内执行：加锁 -> 二次检查 -> 插入/flush -> 提交）
    try:
        # 使用会话的自动事务，避免显式 begin() 导致“已存在事务”的错误
        # 3a. 在支持的数据库上锁定父节点，缩短锁时间窗口
        _ = crud.lock_node_for_update(db, request.node_id)
        # 3b. 再次检查是否已被并发请求创建（双重校验）
        concurrent_child = crud.get_child_by_parent_and_choice(
            db, request.session_id, request.node_id, request.choice.strip()
        )
        if concurrent_child:
            new_node = concurrent_child
        else:
            new_node = crud.create_story_node(
                db,
                session_id=request.session_id,
                segment=raw_data,
                parent_id=request.node_id,
                user_choice=request.choice.strip(),
                commit=False,
            )
        # 明确提交事务
        db.commit()
    except IntegrityError:
        # 可能在提交时触发唯一约束，说明并发请求已创建相同子节点
        db.rollback()
        new_node = crud.get_child_by_parent_and_choice(
            db, request.session_id, request.node_id, request.choice.strip()
        )
        if not new_node:
            raise

    # 4. 【核心修改】在这里调用一次 calculate_chapter_number 即可
    chapter_number = crud.calculate_chapter_number(db, request.session_id, new_node.id)

    # 5. 组合响应
    metadata = {
        **(raw_data.metadata or {}),
        "chapter_number": chapter_number
    }
    # 将 ChoiceOption 实例转换为字典，避免 Pydantic 类型身份不一致导致的校验错误
    choices_payload = [
        c.model_dump() if hasattr(c, "model_dump") else c
        for c in (raw_data.choices or [])
    ]
    result = schemas.story.StorySegment(
        session_id=request.session_id,
        node_id=new_node.id,
        text=raw_data.text,
        choices=choices_payload,
        image_url=raw_data.image_url,
        success_rate=raw_data.success_rate,
        metadata=_sanitize_metadata(metadata)
    )

    LOGGER.info("故事继续生成成功")
    LOGGER.info(f"[Continue] 🔮 触发动态窗口补齐(新子节点): session={request.session_id}, node={new_node.id}, depth={settings.speculation_max_depth}")
    speculation_service.enqueue(request.session_id, new_node.id, depth=settings.speculation_max_depth)
    return result


# 【核心修改】修改 /retry 端点的函数签名和请求处理
@router.post("/retry", response_model=schemas.story.StorySegment)
async def retry_from_node(
    request: schemas.story.StoryRetryRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    从某个故事节点重新开始

    Args:
        request: 包含 "node_id" 的请求，node_id是玩家后悔的那个选择所产生的节点ID

    Returns:
        StorySegment: 玩家可以重新开始的那个父节点的完整信息
    """
    node_id = request.node_id  # 直接从验证过的模型中获取
    LOGGER.info(f"收到时空回溯请求，目标节点: {node_id}")

    try:
        # 权限与归属校验
        original_node = crud.get_node_by_id(db, node_id)
        if not original_node:
            raise ValueError("节点不存在")
        session = crud.get_session_by_id(db, original_node.session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该游戏会话")

        # 【核心修改】调用新的 CRUD 函数
        target_node = crud.prune_story_after_node(db, node_id)

        # 计算回溯点的章节号
        chapter_number = crud.calculate_chapter_number(db, target_node.session_id, target_node.id)

        # 将返回的 SQLAlchemy 模型对象转换为 Pydantic 模型
        result = schemas.story.StorySegment(
            session_id=target_node.session_id,
            node_id=target_node.id,
            text=target_node.story_text,
            choices=target_node.get_choices(),
            image_url=target_node.image_url,
            success_rate=target_node.success_rate,
            metadata={"source": "retry", "chapter_number": chapter_number}
        )
        return result

    except ValueError as e:
        LOGGER.error(f"时空回溯失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        LOGGER.error(f"处理回溯请求时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="时空回溯时发生未知错误")


# --- 重生编年史 (Chronicle) API ---

@router.get("/sessions/{session_id}/latest", response_model=schemas.story.StorySegment)
async def get_latest_node_for_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取指定会话的最新节点以继续游戏 (需要认证)"""
    LOGGER.info(f"[latest] user={current_user.id} querying session_id={session_id}")
    node = crud.get_latest_node_by_session(db, session_id=session_id, user_id=current_user.id)
    
    if not node:
        LOGGER.warning(f"[latest] no node found for session_id={session_id} or not owned by user")
        raise HTTPException(status_code=404, detail="找不到该游戏会话的最新节点，或该会话不属于你")

    chapter_number = crud.calculate_chapter_number(db, node.session_id, node.id)
    
    metadata = {
        "source": "continue",
        "chapter_number": chapter_number
    }
    metadata = _sanitize_metadata(metadata)
    segment = schemas.story.StorySegment(
        session_id=node.session_id,
        node_id=node.id,
        text=node.story_text,
        choices=node.get_choices(),
        image_url=node.image_url,
        success_rate=node.success_rate,
        metadata=metadata
    )
    LOGGER.info(f"[latest] returning node_id={segment.node_id} session_id={segment.session_id} chapter={chapter_number} choices={len(segment.choices) if segment.choices else 0}")
    return segment

@router.get("/sessions", response_model=List[schemas.story.GameSessionSummary])
async def get_user_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取当前登录用户的所有游戏会话列表 (需要认证)"""
    sessions = crud.get_sessions_by_user(db, user_id=current_user.id)
    return sessions

@router.get("/latest", response_model=schemas.story.StorySegment)
async def get_user_latest_node(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取当前用户所有会话中的最新节点（用于最可信的继续游戏）"""
    LOGGER.info(f"[latest-global] user={current_user.id} querying deepest progress across all sessions")
    node = crud.get_deepest_node_for_user(db, user_id=current_user.id)
    if not node:
        LOGGER.warning(f"[latest-global] user={current_user.id} has no nodes across any sessions")
        raise HTTPException(status_code=404, detail="你还没有任何游戏进度")

    chapter_number = crud.calculate_chapter_number(db, node.session_id, node.id)
    metadata = {
        "source": "continue",
        "chapter_number": chapter_number
    }
    metadata = _sanitize_metadata(metadata)
    segment = schemas.story.StorySegment(
        session_id=node.session_id,
        node_id=node.id,
        text=node.story_text,
        choices=node.get_choices(),
        image_url=node.image_url,
        metadata=metadata
    )
    LOGGER.info(f"[latest-global] returning node_id={segment.node_id} session_id={segment.session_id} chapter={chapter_number} choices={len(segment.choices) if segment.choices else 0}")
    return segment

@router.get("/sessions/{session_id}", response_model=schemas.story.GameSessionDetail)
async def get_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取单个游戏会话的详细历史 (需要认证)"""
    session = crud.get_session_details(db, session_id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="找不到该游戏会话，或该会话不属于你")

    # 仅提取已确认（非预生成）的节点，避免提前剧透
    confirmed_nodes = crud.get_session_history(db, session.id)

    # 手动构建响应模型，因为数据库模型和Pydantic模型结构不完全匹配
    nodes_details = []
    for i, node in enumerate(confirmed_nodes):
        nodes_details.append(schemas.story.StoryNodeDetail(
            id=node.id,
            story_text=node.story_text,
            image_url=node.image_url,
            user_choice=node.user_choice,
            choices=node.get_choices(),
            chapter_number=i + 1
        ))

    return schemas.story.GameSessionDetail(
        id=session.id,
        wish=session.wish,
        created_at=session.created_at,
        nodes=nodes_details
    )


@router.post("/saves", response_model=schemas.story.StorySaveDetail)
async def create_story_save_endpoint(
    request: schemas.story.StorySaveCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = crud.get_session_by_id(db, request.session_id)
    _ensure_session_ownership(session, current_user.id)

    node = crud.get_node_by_id(db, request.node_id)
    _ensure_node_belongs_to_session(node, request.session_id)

    save = crud.create_story_save(
        db,
        session_id=request.session_id,
        node_id=request.node_id,
        title=request.title,
    )
    return _build_save_detail(db, save)


@router.get("/saves", response_model=List[schemas.story.StorySaveSummary])
async def list_story_saves_endpoint(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    status_value = status_filter.strip() if status_filter else None
    if status_value and status_value not in SAVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法的存档状态过滤")

    saves = crud.list_story_saves(db, current_user.id, status=status_value)
    return [
        schemas.story.StorySaveSummary(
            id=save.id,
            session_id=save.session_id,
            node_id=save.node_id,
            title=save.title,
            status=save.status,
            created_at=save.created_at,
            updated_at=save.updated_at,
        )
        for save in saves
    ]


@router.get("/saves/{save_id}", response_model=schemas.story.StorySaveDetail)
async def get_story_save_detail_endpoint(
    save_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    save = crud.get_story_save(db, save_id, current_user.id)
    if not save:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到存档")
    return _build_save_detail(db, save)


@router.patch("/saves/{save_id}", response_model=schemas.story.StorySaveDetail)
async def update_story_save_endpoint(
    save_id: int,
    request: schemas.story.StorySaveUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    save = crud.get_story_save(db, save_id, current_user.id)
    if not save:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到存档")

    new_status: Optional[str] = request.status
    if new_status and new_status not in SAVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法的存档状态")

    updated = crud.update_story_save(db, save_id, title=request.title, status=new_status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="存档更新失败")

    return _build_save_detail(db, updated)


@router.delete("/saves/{save_id}", response_model=schemas.story.StorySaveSummary)
async def delete_story_save_endpoint(
    save_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    save = crud.get_story_save(db, save_id, current_user.id)
    if not save:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到存档")

    summary = schemas.story.StorySaveSummary(
        id=save.id,
        session_id=save.session_id,
        node_id=save.node_id,
        title=save.title,
        status=save.status,
        created_at=save.created_at,
        updated_at=save.updated_at,
    )

    if not crud.delete_story_save(db, save_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除存档失败")

    return summary



@router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {"status": "healthy", "service": "story_api"}


@router.get("/metrics")
async def get_metrics():
    """返回服务端关键运行指标（LLM 与 推演服务）。"""
    try:
        from core.llm_clients import llm_client
        llm_metrics = getattr(llm_client, "get_metrics", lambda: {} )()
    except Exception as e:  # noqa: BLE001
        llm_metrics = {"error": str(e)}

    try:
        spec_metrics = speculation_get_metrics()
    except Exception as e:  # noqa: BLE001
        spec_metrics = {"error": str(e)}

    return {
        "llm": llm_metrics,
        "speculation": spec_metrics,
    }


# 注意：异常处理器应该在主应用中定义，不是在路由器中
