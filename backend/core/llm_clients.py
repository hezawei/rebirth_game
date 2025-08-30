"""
大语言模型客户端封装
支持多种LLM供应商，便于未来切换
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from .model_config import get_current_config
from config.logging_config import LOGGER


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    def generate(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """生成文本"""
        pass


class UniversalLLMClient(BaseLLMClient):
    """
    通用LLM客户端
    根据配置自动适配不同的模型供应商（豆包、OpenAI、Gemini等）
    """

    def __init__(self):
        # 获取当前模型配置
        self.model_config = get_current_config()

        # 初始化OpenAI兼容的客户端
        import openai
        client_params = self.model_config.get_client_params()
        self.client = openai.OpenAI(**client_params)

        LOGGER.info(f"LLM客户端初始化成功 - 模型: {self.model_config.model_name}")
        LOGGER.info(f"API地址: {self.model_config.base_url}")

    def generate(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """生成文本"""
        messages = []

        # 添加历史对话
        if history:
            messages.extend(history)

        # 添加当前提示
        messages.append({"role": "user", "content": prompt})

        # 获取模型特定的参数
        completion_params = self.model_config.get_completion_params()
        completion_params["messages"] = messages

        # 调用模型
        response = self.client.chat.completions.create(**completion_params)

        result = response.choices[0].message.content

        # 记录使用情况
        if hasattr(response, 'usage') and response.usage:
            LOGGER.info(f"模型生成成功 - 模型: {self.model_config.model_name}, "
                       f"tokens使用: {response.usage.total_tokens}")
        else:
            LOGGER.info(f"模型生成成功 - 模型: {self.model_config.model_name}")

        return result


# 全局客户端实例
llm_client = UniversalLLMClient()
