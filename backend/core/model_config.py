"""
大模型配置文件
支持多种模型供应商，便于扩展和切换
"""

from typing import Dict, Any, Optional
from config.settings import settings
from abc import ABC, abstractmethod


class ModelConfig(ABC):
    """模型配置基类"""
    
    provider_type: str 
    api_key: str
    base_url: str
    model_name: str
    completion_params: Dict[str, Any]

    def __init__(self, provider_name: str):
        config = settings.LLM_PROVIDERS.get(provider_name)
        if not config:
            raise ValueError(f"在 settings.LLM_PROVIDERS 中未找到 '{provider_name}' 的配置")

        self.provider_type = config["provider_type"]
        self.api_key = config.get("api_key", "")
        self.base_url = config["base_url"]
        self.model_name = config["model"]
        self.completion_params = config.get("completion_params", {})

    def get_client_params(self) -> Dict[str, Any]:
        """获取客户端初始化参数"""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url
        }
    
    def get_completion_params(self) -> Dict[str, Any]:
        """获取对话完成参数"""
        # 返回一个副本以防止外部修改原始配置
        params = self.completion_params.copy()
        params['model'] = self.model_name
        return params


class DoubaoConfig(ModelConfig):
    """豆包模型配置"""
    def __init__(self):
        super().__init__("doubao")


class SiliconFlowConfig(ModelConfig):
    """硅基流动模型配置 (OpenAI兼容) - 现用于DashScope"""
    def __init__(self):
        super().__init__("dashscope")


class OpenAIConfig(ModelConfig):
    """OpenAI模型配置"""
    def __init__(self):
        super().__init__("openai")




# 模型配置映射
MODEL_CONFIGS = {
    "doubao": DoubaoConfig,
    "openai": OpenAIConfig,
    "dashscope": SiliconFlowConfig, # 复用OpenAI兼容配置类
}


def get_model_config(model_type: str = "doubao") -> ModelConfig:
    """
    获取指定类型的模型配置
    
    Args:
        model_type: 模型类型 ("doubao", "openai", "gemini")
        
    Returns:
        ModelConfig: 对应的模型配置实例
        
    Raises:
        ValueError: 不支持的模型类型
    """
    if model_type not in MODEL_CONFIGS:
        raise ValueError(f"不支持的模型类型: {model_type}. 支持的类型: {list(MODEL_CONFIGS.keys())}")
    
    config_class = MODEL_CONFIGS[model_type]
    return config_class()


def get_current_model_config() -> ModelConfig:
    """依据配置选择当前模型。"""
    provider_name = (settings.llm_provider or "").strip().lower() or "doubao"

    provider_config = settings.LLM_PROVIDERS.get(provider_name)
    if not provider_config:
        raise ValueError(f"未知的 llm_provider: '{provider_name}'")

    # 检查 API key 是否存在
    if not provider_config.get("api_key"):
        raise ValueError(f"当前配置为 {provider_name}，但未在 settings.LLM_PROVIDERS 中设置 api_key")

    # 直接使用 provider_name 获取配置
    return get_model_config(provider_name)


# 当前使用的模型配置 - 延迟初始化
current_model_config = None

def get_current_config():
    """获取当前模型配置，支持延迟初始化"""
    global current_model_config
    if current_model_config is None:
        current_model_config = get_current_model_config()
    return current_model_config
