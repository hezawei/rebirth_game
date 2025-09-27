"""
内容安全与敏感词校验
可根据需要扩展为外部服务（如平台内容安全接口）。
当前实现：基于内置词表的本地校验，开箱即用。
"""
from typing import Tuple, Optional, List, Dict
import logging
from .llm_clients import llm_client

# 基础违禁词表（示例，可扩展）
BASIC_BANNED_WORDS: Dict[str, List[str]] = {
    "暴恐/极端": ["恐怖主义", "极端主义", "暴恐", "恐袭"],
    "仇恨/歧视": ["种族歧视", "仇恨言论"],
    "违法犯罪": ["毒品", "贩毒", "枪支", "走私", "诈骗"],
    "色情": ["色情", "淫秽"],
}


def check_wish_safety(wish: str) -> Tuple[bool, Optional[Dict[str, str]]]:
    """对愿望进行基础敏感词与长度校验。
    返回 (ok, result)。ok=False 时提供具体原因。
    """
    text = (wish or "").strip()
    if not text:
        return False, {"reason": "重生愿望不能为空"}
    if len(text) > 100:
        return False, {"reason": "重生愿望过长，请控制在100字以内"}

    lowered = text.lower()
    for category, words in BASIC_BANNED_WORDS.items():
        for word in words:
            if word and word.lower() in lowered:
                logging.warning(f"检测到敏感词：{word}，分类：{category}")
                return False, {"reason": f"包含敏感词：{word}", "category": category}

    return True, None


def check_wish_safety_llm(wish: str) -> Tuple[bool, Optional[str]]:
    """使用LLM进行高级愿望校验，仅返回通过/不通过。
    专门优化为快速响应，只输出true/false。
    """
    text = (wish or "").strip()
    if not text:
        return False, "愿望不能为空"
    
    # 先做基础校验
    basic_ok, basic_info = check_wish_safety(text)
    if not basic_ok:
        return False, basic_info.get("reason", "不合适的愿望")
    
    # LLM校验提示词：专门优化为快速判断
    prompt = f"""判断以下重生愿望是否合适。只能回答'true'或'false'，不要任何解释。

合适标准：积极正面，不涉及违法犯罪、仇恨歧视、色情暴力、自伤他伤等内容。

愿望：{text}

回答（只能是true或false）："""
    
    try:
        # 使用最小token数和低温度快速判断
        response = llm_client.generate(
            prompt, 
            history=None,
            temperature=0.1,
            max_tokens=10  # 只需要输出true/false
        )
        result = str(response).strip().lower()
        
        if "true" in result:
            return True, None
        elif "false" in result:
            return False, "愿望内容不合适，请重新输入"
        else:
            # LLM输出异常，默认通过基础校验
            logging.warning(f"LLM愿望校验输出异常: {response}")
            return True, None
            
    except Exception as e:
        # LLM服务异常，回退到基础校验
        logging.error(f"LLM愿望校验失败: {e}")
        return True, None
