"""
核心故事生成引擎
负责协调LLM调用、图片选择和故事状态管理
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.logging_config import LOGGER
from config.settings import settings

from . import prompt_templates
from .history_context import build_prompt_context
from .image_service import image_service
from .llm_clients import llm_client
from backend.schemas.story import ChoiceOption, RawStoryData


class StoryEngine:
    """故事生成引擎"""

    def __init__(self):
        LOGGER.info("故事引擎初始化完成")
    
    # ---------------- ChapterFlow helpers ----------------
    def _get_config(self) -> Dict[str, int]:
        """获取ChapterFlow的阈值配置。"""
        return {
            "min_nodes": int(getattr(settings, "min_nodes", 6)),
            "max_nodes": int(getattr(settings, "max_nodes", 22)),
            "pass_threshold": int(getattr(settings, "pass_threshold", 80)),
            "fail_threshold": int(getattr(settings, "fail_threshold", 90)),
        }

    def _clamp(self, v: int, lo: int = 0, hi: int = 100) -> int:
        return max(lo, min(hi, int(v)))

    def _apply_effects(self, state: Dict[str, int], eff: Dict[str, Any]) -> Dict[str, int]:
        p = self._clamp(state.get("progress", 0) + int(eff.get("delta_progress", 0)))
        r = self._clamp(state.get("risk", 0) + int(eff.get("delta_risk", 0)))
        e = self._clamp(state.get("exposure", 0) + int(eff.get("delta_exposure", 0)))
        return {"progress": p, "risk": r, "exposure": e}

    def _get_hint(self, delta: int) -> str:
        if delta >= 10:
            return "up_big"
        if delta >= 5:
            return "up_mid"
        if delta >= 2:
            return "up_small"
        if delta <= -10:
            return "down_big"
        if delta <= -5:
            return "down_mid"
        if delta <= -2:
            return "down_small"
        return "flat"

    def _get_micro_feedback(self, prev: Dict[str, int], cur: Dict[str, int]) -> Dict[str, str]:
        dp = cur.get("progress", 0) - prev.get("progress", 0)
        dr = cur.get("risk", 0) - prev.get("risk", 0)
        de = cur.get("exposure", 0) - prev.get("exposure", 0)
        # 简洁中文提示（避免剧透）
        msg_parts: List[str] = []
        if dp >= 5:
            msg_parts.append("推进显著")
        elif dp >= 2:
            msg_parts.append("推进可见")
        elif dp <= -2:
            msg_parts.append("推进受挫")
        if dr >= 5:
            msg_parts.append("风声渐紧")
        elif dr <= -2:
            msg_parts.append("风险回落")
        if de >= 4:
            msg_parts.append("曝光上扬")
        elif de <= -2:
            msg_parts.append("更为隐蔽")
        micro = "，".join(msg_parts) or "风向未明"
        return {
            "progress_hint": self._get_hint(dp),
            "risk_hint": self._get_hint(dr),
            "exposure_hint": self._get_hint(de),
            "micro_message": micro,
        }

    def _should_settle(self, state: Dict[str, int], nodes_count: int, cfg: Dict[str, int], deadlock: bool = False) -> Optional[str]:
        if state.get("risk", 0) >= cfg["fail_threshold"] or state.get("exposure", 0) >= cfg["fail_threshold"]:
            return "fail"
        if nodes_count >= cfg["max_nodes"]:
            return "auto"
        if nodes_count >= cfg["min_nodes"] and state.get("progress", 0) >= cfg["pass_threshold"]:
            return "success"
        if deadlock:
            return "fail"
        return None

    def _compute_grade(self, state: Dict[str, int]) -> str:
        base = float(state.get("progress", 0))
        penalty = max(0.0, float(state.get("risk", 0) - 70)) * 0.6 + max(0.0, float(state.get("exposure", 0) - 70)) * 0.4
        final = self._clamp(int(round(base - penalty)))
        if final >= 90:
            return "S"
        if final >= 75:
            return "A"
        if final >= 60:
            return "B"
        return "C"

    def _generate_image_token(self, wish: str) -> str:
        # 简易连续性token：去空白+时间戳片段
        base = re.sub(r"\s+", "-", str(wish))[:24]
        return f"{base}-{datetime.now().strftime('%H%M%S')}"

    def _parse_node(self, raw_response: str) -> Dict[str, Any]:
        """解析NODE_PROMPT返回：text、choices(含 effects)、image_prompts、image_continuity_token。"""
        json_str = self._extract_json(raw_response)
        try:
            data = json.loads(json_str)
        except Exception as e:
            LOGGER.error(f"解析节点JSON失败: {e}; 预览={json_str[:200]!r}")
            # 尝试修复
            fixed = self._attempt_json_fix(raw_response)
            data = fixed
        if not isinstance(data, dict) or "text" not in data or "choices" not in data:
            raise ValueError("节点缺少必要字段 'text' 或 'choices'")
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 3:
            raise ValueError("节点必须返回3个choices")
        hidden_map: Dict[str, Dict[str, Any]] = {}
        normalized_choices: List[Dict[str, Any]] = []
        for ch in choices:
            if not isinstance(ch, dict) or "option" not in ch or "summary" not in ch:
                raise ValueError("choice 项缺少 'option' 或 'summary'")
            opt = str(ch["option"]).strip()
            eff = ch.get("effects") or {}
            if not isinstance(eff, dict):
                eff = {}
            hidden_map[opt] = {
                "delta_progress": int(eff.get("delta_progress", 0)),
                "delta_risk": int(eff.get("delta_risk", 0)),
                "delta_exposure": int(eff.get("delta_exposure", 0)),
                "tags": ch.get("effects", {}).get("tags") if isinstance(ch.get("effects"), dict) else None,
            }
            normalized_choices.append({
                "option": opt,
                "summary": str(ch["summary"]).strip(),
            })
        return {
            "text": str(data["text"]),
            "choices_display": normalized_choices,
            "hidden_effects_map": hidden_map,
            "image_prompts": data.get("image_prompts") or [],
            "image_token": data.get("image_continuity_token") or None,
        }

    def _attempt_json_fix(self, raw_response: str) -> Dict[str, Any]:
        """当节点解析失败时，请模型修复为严格的JSON结构。"""
        try:
            if not raw_response or len(str(raw_response).strip()) < 10:
                raise ValueError("LLM 原始响应为空，无法修复")
            fixer_body = (
                "请将以下内容转换为严格的JSON对象，键只允许：text, choices, image_prompts, image_continuity_token。\n"
                "要求：\n"
                "- choices 必须是长度为3的数组；\n"
                "- 每个choice对象必须包含 option(字符串)、summary(字符串)、effects(对象)；\n"
                "- effects 对象必须包含 delta_progress(int)、delta_risk(int)、delta_exposure(int)，可选 tags(string[])；\n"
                "- 仅输出纯JSON，不要Markdown代码块、不要额外文字。\n\n"
                "原始内容如下：\n<<<\n" + str(raw_response) + "\n>>>\n"
            )
            preamble = (
                "你是交互叙事引擎。严格只输出一个JSON对象，不含任何Markdown或额外文字。"
                "本次允许的顶层键：text, choices, image_prompts, image_continuity_token。"
                "其中 choices 为长度3的数组，每项仅包含 option, summary, effects(含 delta_progress, delta_risk, delta_exposure, 可选tags)。"
                "禁止输出 success_rate 或 success_rate_delta 等任何评分相关字段。"
            )
            fixed = llm_client.generate(
                fixer_body,
                history=None,
                model=None,
                temperature=0.1,
                max_tokens=2000,
                system_preamble_override=preamble,
            )
            fixed_json = self._extract_json(fixed)
            return json.loads(fixed_json)
        except Exception as e:
            LOGGER.error(f"[JSON-FIX] 修复失败: {e}; 原始预览={str(raw_response)[:200]!r}")
            raise
    
    def _extract_json(self, raw_response: str) -> str:
        """
        从原始模型输出中提取 JSON 字符串：
        - 去除可能存在的 ```json ... ``` 代码块包裹
        - 若仍有前后噪声，则从首个 '{' 开始，按括号配对截取到对应的 '}'
        """
        if raw_response is None:
            raise ValueError("LLM返回为空")

        s = str(raw_response).strip()
        LOGGER.debug(f"[JSON] 原始长度={len(s)} 预览={s[:160]!r}")

        # 1) 去除 ```json 代码围栏
        fence = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.IGNORECASE | re.DOTALL)
        m = fence.match(s)
        if m:
            inner = m.group(1).strip()
            LOGGER.debug(f"[JSON] 捕获到Markdown代码围栏，内层长度={len(inner)} 预览={inner[:160]!r}")
            return inner

        # 2) 若包含冗余文本，尝试从首个 '{' 起按括号配对截取（忽略字符串内部的大括号）
        start = s.find('{')
        if start == -1:
            # 无 JSON 起始符，直接返回（调用方将尝试回退）
            LOGGER.warning("[JSON] 未发现 '{' 起始符，可能非JSON输出")
            return s
        depth = 0
        end = None
        in_str = False
        escape = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            else:
                if ch == '"':
                    in_str = True
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if end is not None:
            frag = s[start:end+1].strip()
            LOGGER.debug(f"[JSON] 括号配对提取成功，长度={len(frag)} 预览={frag[:160]!r}")
            return frag
        frag = s[start:].strip()
        LOGGER.debug(f"[JSON] 未找到完整闭合，返回起始到末尾片段，长度={len(frag)} 预览={frag[:160]!r}")
        return frag

    def _normalize_choices(self, choices_payload: Any) -> List[ChoiceOption]:
        if not isinstance(choices_payload, list):
            raise ValueError("choices 字段必须是包含选项对象的列表")

        normalized: List[ChoiceOption] = []
        for entry in choices_payload:
            if not isinstance(entry, dict):
                raise ValueError("choices 列表中的元素必须是 JSON 对象")

            missing = {k for k in ("option", "summary", "success_rate_delta") if k not in entry}
            if missing:
                raise ValueError(f"选项缺少必要字段: {missing}")

            option_text = str(entry["option"]).strip()
            if not option_text:
                raise ValueError("选项文本不能为空")

            summary_text = str(entry["summary"]).strip()
            try:
                delta = int(entry["success_rate_delta"])
            except Exception as exc:
                raise ValueError("success_rate_delta 必须是整数") from exc

            if delta < -100 or delta > 100:
                raise ValueError("success_rate_delta 必须在 -100 到 100 范围内")

            risk_level = entry.get("risk_level")
            if risk_level is not None:
                risk_level = str(risk_level).strip()

            tags = entry.get("tags") or []
            if not isinstance(tags, list):
                raise ValueError("tags 必须是字符串列表")
            tags = [str(tag).strip() for tag in tags if str(tag).strip()]

            normalized.append(
                ChoiceOption(
                    option=option_text,
                    summary=summary_text,
                    success_rate_delta=delta,
                    risk_level=risk_level or None,
                    tags=tags or None,
                )
            )

        if len(normalized) != 3:
            raise ValueError("故事引擎要求精确返回 3 个选择")

        return normalized

    def _parse_llm_response(self, raw_response: str) -> Dict[str, Any]:
        """解析LLM的JSON响应（健壮版，带一次性回退修复）"""
        json_str = self._extract_json(raw_response)
        LOGGER.info(f"[JSON] 提取后长度={len(json_str)} 预览={json_str[:200]!r}")
        if not json_str or not json_str.strip().startswith('{'):
            LOGGER.warning("[JSON] 首次提取得到的内容为空或非JSON对象，尝试回退修复")
            data = self._attempt_json_fix(raw_response)
        else:
            try:
                data = json.loads(json_str)
            except Exception as e:
                LOGGER.error(f"[JSON] 直接解析失败: {e}; json_str预览={json_str[:200]!r}")
                data = self._attempt_json_fix(raw_response)

        # 验证必要字段
        if "text" not in data or "choices" not in data:
            LOGGER.error(f"LLM响应缺少必要字段: {raw_response}")
            raise ValueError(f"响应缺少必要字段: {data}")

        choices = self._normalize_choices(data["choices"])

        if "success_rate" not in data:
            LOGGER.warning("[JSON] 响应中缺少 'success_rate' 字段，将使用默认值 50")
            success_rate = 50
        else:
            try:
                success_rate = int(data["success_rate"])
            except (ValueError, TypeError):
                LOGGER.warning(f"[JSON] 'success_rate' 字段无法转换为整数（值为: {data['success_rate']!r}），将使用默认值 50")
                success_rate = 50

        if success_rate < 0 or success_rate > 100:
            raise ValueError("success_rate 必须在 0 到 100 之间")

        extra_payload = {
            key: value
            for key, value in data.items()
            if key not in {"text", "success_rate", "choices"}
        }

        return {
            "text": data["text"],
            "success_rate": success_rate,
            "choices": choices,
            "extra": extra_payload,
        }

    def _attempt_json_fix(self, raw_response: str) -> Dict:
        """当直接解析失败时，请模型将输出转换为严格JSON，仅尝试一次。"""
        try:
            # 检查原始响应是否为空或太短
            if not raw_response or len(str(raw_response).strip()) < 10:
                raise ValueError("LLM 原始响应为空，无法修复")
            
            fixer_prompt = (
                "你是一个严格的JSON修复器。请将以下内容转换为一个严格的JSON对象，"
                "必须包含键 'text' (字符串)、'success_rate' (0-100 的整数)、'choices' (长度为3的对象数组)。\n"
                "其中每个 choice 对象必须包含 'option'(字符串)、'summary'(字符串)、'success_rate_delta'(整数，-100~100)，"
                "可选 'risk_level'(字符串) 和 'tags'(字符串数组)。\n"
                "输出要求：仅输出JSON本体，不要使用Markdown代码块或任何额外文字。\n\n"
                "原始内容如下：\n<<<\n" + str(raw_response) + "\n>>>\n"
            )
            # 避免递归：本方法不再递归调用自身
            fixed = llm_client.generate(
                fixer_prompt,
                history=None,
                model=None,
                temperature=0.1,
                max_tokens=2000, # 提高修复任务的令牌限制
            )
            LOGGER.debug(f"[JSON-FIX] 修复返回长度={len(str(fixed))} 预览={str(fixed)[:200]!r}")
            
            # 再次检查修复后的响应
            if not fixed or len(str(fixed).strip()) < 10:
                raise ValueError("LLM 修复响应为空，无法解析")

            fixed_json = self._extract_json(fixed)
            return json.loads(fixed_json)
        except Exception as e:
            LOGGER.error(f"[JSON-FIX] 修复失败: {e}; 原始预览={str(raw_response)[:200]!r}")
            raise

    def start_story(self, wish: str) -> RawStoryData:
        """开始新的故事"""
        LOGGER.info(f"收到新的故事开始请求，愿望是: '{wish}'")
        prompt_context = build_prompt_context(wish)
        # 使用 ChapterFlow 流程
        cfg = self._get_config()
        image_token = self._generate_image_token(wish)
        prompt = prompt_templates.NODE_PROMPT.format(
                history_context=prompt_context["context_block"],
                image_token=image_token,
            )
        preamble = (
            "你是交互叙事引擎。严格只输出一个JSON对象，不含任何Markdown或额外文字。"
            "本次允许的顶层键：text, choices, image_prompts, image_continuity_token。"
            "其中 choices 为长度3的数组，每项仅包含 option, summary, effects(含 delta_progress, delta_risk, delta_exposure, 可选tags)。"
            "禁止输出 success_rate 或 success_rate_delta 等任何评分相关字段。"
        )
        raw_response = llm_client.generate(prompt, system_preamble_override=preamble)
        LOGGER.info(f"[LLM raw][start] 长度={len(str(raw_response))} 预览={str(raw_response)[:300]!r}")
        parsed = self._parse_node(raw_response)
        story_text = parsed["text"]
        
        # 构造展示choices（隐藏effects不外露）
        display_choices = []
        for ch in parsed["choices_display"]:
            display_choices.append(
                ChoiceOption(
                    option=ch["option"],
                    summary=ch["summary"],
                    success_rate_delta=None,  # 完全移除评分显示
                    risk_level=None,
                    tags=None,
                )
            )
        
        # 【图像生成】直接使用主要的图像服务逻辑：AI优先，失败则随机图库
        image_url = image_service.get_image_for_story(story_text)
        chapter_meta = {
            "enabled": True,
            "config": cfg,
            "state": {"progress": 0, "risk": 0, "exposure": 0},
            "timeline": [],
            "node_index": 1,
            "image_token": parsed.get("image_token") or image_token,
            "hidden_effects_map": parsed["hidden_effects_map"],  # 仅供后续引擎读取
        }
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "wish": wish,
            "type": "start",
            "chapter_number": 1,
            "history_profile": prompt_context["profile_dict"],
            "recommended_chapter_count": prompt_context["recommended_chapter_count"],
            "anchor_events": prompt_context["anchor_events"],
            "chapter": chapter_meta,
        }
        result = RawStoryData(
            text=story_text,
            choices=display_choices,
            image_url=image_url,
            success_rate=None,  # 完全移除成功率
            metadata=metadata,
        )
        LOGGER.info("新故事生成成功")
        return result

    
    def continue_story(
        self,
        wish: str,
        story_history: List[Dict[str, str]],
        choice: str,
        *,
        chapter_number: int,
        current_success_rate: Optional[int],
        parent_metadata: Optional[Dict[str, Any]] = None,
    ) -> RawStoryData:
        """继续故事"""
        LOGGER.info(f"继续故事，用户选择: {choice}")

        # success_rate可能为None（隐藏数值），这是正常的
        prompt_context = build_prompt_context(wish)
        
        # 取父节点的章节状态
        chapter_data = (parent_metadata or {}).get("chapter") if isinstance(parent_metadata, dict) else None
        cfg = self._get_config()
        state_prev = {"progress": 0, "risk": 0, "exposure": 0}
        node_index_prev = 1
        image_token = self._generate_image_token(wish)
        timeline_prev: List[Dict[str, Any]] = []
        
        if isinstance(chapter_data, dict):
            state_prev = dict(chapter_data.get("state") or state_prev)
            node_index_prev = int(chapter_data.get("node_index") or node_index_prev)
            image_token = chapter_data.get("image_token") or image_token
            timeline_prev = list(chapter_data.get("timeline") or [])

        prompt = prompt_templates.NODE_PROMPT.format(
            history_context=prompt_context["context_block"],
            image_token=image_token,
        )
        preamble = (
            "你是交互叙事引擎。严格只输出一个JSON对象，不含任何Markdown或额外文字。"
            "本次允许的顶层键：text, choices, image_prompts, image_continuity_token。"
            "其中 choices 为长度3的数组，每项仅包含 option, summary, effects(含 delta_progress, delta_risk, delta_exposure, 可选tags)。"
            "禁止输出 success_rate 或 success_rate_delta 等任何评分相关字段。"
        )
        raw_response = llm_client.generate(prompt, history=story_history, system_preamble_override=preamble)
        LOGGER.info(f"[LLM raw][continue] 长度={len(str(raw_response))} 预览={str(raw_response)[:300]!r}")
        parsed = self._parse_node(raw_response)
        story_text = parsed["text"]

        # 应用选择的隐藏影响
        heff_map = parsed["hidden_effects_map"]
        eff = heff_map.get(choice) or {"delta_progress": 0, "delta_risk": 0, "delta_exposure": 0}
        state_cur = self._apply_effects(state_prev, eff)
        micro = self._get_micro_feedback(state_prev, state_cur)

        # 更新时间线（用选项summary作为影响叙述的基础）
        chosen_summary = None
        for ch in parsed["choices_display"]:
            if ch.get("option") == choice:
                chosen_summary = ch.get("summary")
                break
        timeline = timeline_prev + [{
            "node": node_index_prev,
            "choice": choice,
            "impact": chosen_summary or "",
        }]

        # 结算判定
        settle = self._should_settle(state_cur, nodes_count=node_index_prev, cfg=cfg, deadlock=False)
        settlement_payload: Optional[Dict[str, Any]] = None
        grade = self._compute_grade(state_cur)
        result_tag = None
        if settle is not None:
            result_tag = "success" if settle == "success" else ("fail" if settle == "fail" else "auto")
            settlement_payload = self._generate_settlement(
                wish=wish,
                timeline=timeline,
                result=result_tag,
                grade=grade,
            )

        # 构造展示choices（隐藏effects不外露），若结算则可返回空choices
        display_choices = []
        if settlement_payload is None:
            for ch in parsed["choices_display"]:
                display_choices.append(
                    ChoiceOption(
                        option=ch["option"],
                        summary=ch["summary"],
                        success_rate_delta=None,
                        risk_level=None,
                        tags=None,
                    )
                )

        # 【图像生成】直接使用主要的图像服务逻辑：AI优先，失败则随机图库
        image_url = image_service.get_image_for_story(story_text)
        chapter_meta = {
            "enabled": True,
            "config": cfg,
            "state": state_cur,
            "timeline": timeline,
            "node_index": node_index_prev + 1,
            "image_token": parsed.get("image_token") or image_token,
            "micro_feedback": micro,
            "settlement": settlement_payload,
            "hidden_effects_map": heff_map,
        }
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "user_choice": choice,
            "type": "continue",
            "history_length": len(story_history),
            "chapter_number": chapter_number + 1,
            "history_profile": prompt_context["profile_dict"],
            "recommended_chapter_count": prompt_context["recommended_chapter_count"],
            "anchor_events": prompt_context["anchor_events"],
            "chapter": chapter_meta,
        }
        result = RawStoryData(
            text=story_text,
            choices=display_choices,
            image_url=image_url,
            success_rate=None,  # 完全移除成功率
            metadata=metadata,
        )
        LOGGER.info("故事继续生成成功")
        return result

    def _generate_settlement(self, *, wish: str, timeline: List[Dict[str, Any]], result: str, grade: str) -> Dict[str, Any]:
        """调用LLM生成章末结算描述（复盘+引子）。"""
        # 组织时间线块
        lines = []
        for item in timeline:
            n = item.get("node")
            c = item.get("choice")
            imp = item.get("impact") or ""
            lines.append(f"- 第{n}步：选择《{c}》，影响：{imp}")
        timeline_block = "\n".join(lines) or "- （时间线极短）"
        prompt = prompt_templates.SETTLEMENT_PROMPT.format(
            timeline_block=timeline_block,
            result=result,
            grade=grade,
        )
        settle_preamble = (
            "你是JSON生成器。严格只输出一个JSON对象，不含Markdown或多余文字。"
            "只允许输出：chapter_summary, timeline, key_impacts, next_chapter_hook, cover_image_prompt 这些键。"
        )
        raw = llm_client.generate(prompt, system_preamble_override=settle_preamble)
        try:
            data = json.loads(self._extract_json(raw))
        except Exception as e:
            LOGGER.warning(f"[V2] 结算JSON解析失败，回退空壳: {e}")
            data = {
                "chapter_summary": "本章收束，故事暂告一段。",
                "timeline": [{"node": t.get("node"), "choice": t.get("choice"), "impact": t.get("impact") or ""} for t in timeline],
                "key_impacts": [],
                "next_chapter_hook": "新的变局正在酝酿……",
                "cover_image_prompt": "写实风 章末总结 构图严谨 光影凝重",
            }
        data["result"] = result
        data["grade"] = grade
        return data

# 全局故事引擎实例
story_engine = StoryEngine()
