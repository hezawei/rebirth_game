"""
核心故事生成引擎
负责协调LLM调用、图片选择和故事状态管理
"""

import json
from datetime import datetime
from typing import List, Dict
from .llm_clients import llm_client
from . import prompt_templates
from .image_service import image_service
from schemas.story import RawStoryData
from config.logging_config import LOGGER


class StoryEngine:
    """故事生成引擎"""

    def __init__(self):
        LOGGER.info("故事引擎初始化完成")
    
    def _parse_llm_response(self, raw_response: str) -> Dict:
        """解析LLM的JSON响应"""
        data = json.loads(raw_response)

        # 验证必要字段
        if "text" not in data or "choices" not in data:
            LOGGER.error(f"LLM响应缺少必要字段: {raw_response}")
            raise ValueError(f"响应缺少必要字段: {data}")

        # 确保choices是列表
        if not isinstance(data["choices"], list):
            # 如果不是列表，尝试将其转换为列表，以增加容错性
            LOGGER.warning(f"LLM返回的choices不是列表，已强制转换: {data['choices']}")
            data["choices"] = [str(data["choices"])]

        # 限制选择数量
        if len(data["choices"]) > 3:
            LOGGER.warning(f"LLM返回了超过3个选项，已截断: {data['choices']}")
            data["choices"] = data["choices"][:3]

        # 【核心修改】移除 choices 为空的错误检查
        # elif len(data["choices"]) == 0:
        #     raise ValueError("响应中没有选择选项")

        return data
    
    def start_story(self, wish: str) -> RawStoryData:
        """开始新的故事"""
        LOGGER.info(f"收到新的故事开始请求，愿望是: '{wish}'")

        # 生成提示词
        prompt = prompt_templates.START_STORY_PROMPT.format(wish=wish)

        # 调用LLM
        raw_response = llm_client.generate(prompt)
        LOGGER.debug(f"LLM原始回应: {raw_response}")

        # 解析响应
        data = self._parse_llm_response(raw_response)
        story_text = data['text']

        # 使用智能图片服务获取图片
        image_url = image_service.get_image_for_story(story_text)
        LOGGER.info(f"成功生成开篇故事，图片为: {image_url}")

        # 创建元数据
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "wish": wish,
            "type": "start"
        }

        result = RawStoryData(
            text=story_text,
            choices=data['choices'],
            image_url=image_url,
            metadata=metadata
        )

        LOGGER.info("新故事生成成功")
        return result
    
    def continue_story(self, story_history: List[Dict[str, str]], choice: str) -> RawStoryData:
        """继续故事"""
        LOGGER.info(f"继续故事，用户选择: {choice}")

        # 生成提示词
        prompt = prompt_templates.CONTINUE_STORY_PROMPT.format(choice=choice)

        # 调用LLM，传入历史对话
        raw_response = llm_client.generate(prompt, history=story_history)
        LOGGER.debug(f"LLM原始回应: {raw_response}")

        # 解析响应
        data = self._parse_llm_response(raw_response)
        story_text = data['text']

        # 使用智能图片服务获取图片
        image_url = image_service.get_image_for_story(story_text)

        # 创建元数据
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "user_choice": choice,
            "type": "continue",
            "history_length": len(story_history)
        }

        result = RawStoryData(
            text=story_text,
            choices=data['choices'],
            image_url=image_url,
            metadata=metadata
        )

        LOGGER.info("故事继续生成成功")
        return result


# 全局故事引擎实例
story_engine = StoryEngine()
