"""
大模型配置文件
支持多种模型供应商，便于扩展和切换
"""

from typing import Dict, Any, Optional
from config.settings import settings


class ModelConfig:
    """模型配置基类"""
    
    def __init__(self):
        self.api_key: str = ""
        self.base_url: str = ""
        self.model_name: str = ""
        self.max_tokens: int = 1000
        self.temperature: float = 0.8
    
    def get_client_params(self) -> Dict[str, Any]:
        """获取客户端初始化参数"""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url
        }
    
    def get_completion_params(self) -> Dict[str, Any]:
        """获取对话完成参数"""
        return {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }


class DoubaoConfig(ModelConfig):
    """豆包模型配置"""
    
    def __init__(self):
        super().__init__()
        self.api_key = settings.doubao_api_key
        self.base_url = settings.doubao_base_url
        self.model_name = settings.doubao_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
    
    def get_completion_params(self) -> Dict[str, Any]:
        """豆包特定的完成参数"""
        params = super().get_completion_params()
        # 豆包支持JSON模式
        params["response_format"] = {"type": "json_object"}
        return params


class OpenAIConfig(ModelConfig):
    """OpenAI模型配置"""
    
    def __init__(self):
        super().__init__()
        self.api_key = settings.openai_api_key
        self.base_url = "https://api.openai.com/v1"  # OpenAI默认地址
        self.model_name = settings.default_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
    
    def get_completion_params(self) -> Dict[str, Any]:
        """OpenAI特定的完成参数"""
        params = super().get_completion_params()
        params["response_format"] = {"type": "json_object"}
        return params


class GeminiConfig(ModelConfig):
    """Gemini模型配置（预留）"""
    
    def __init__(self):
        super().__init__()
        self.api_key = settings.google_api_key or ""
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model_name = "gemini-pro"
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature


# 模型配置映射
MODEL_CONFIGS = {
    "doubao": DoubaoConfig,
    "openai": OpenAIConfig,
    "gemini": GeminiConfig,
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
    """
    获取当前配置的模型
    根据环境变量自动选择可用的模型
    """
    # 优先级：豆包 > OpenAI > Gemini
    if settings.doubao_api_key and settings.doubao_api_key.strip():
        return get_model_config("doubao")
    elif hasattr(settings, 'openai_api_key') and settings.openai_api_key and settings.openai_api_key.strip():
        return get_model_config("openai")
    elif settings.google_api_key and settings.google_api_key.strip():
        return get_model_config("gemini")
    else:
        raise ValueError("未配置任何可用的模型API密钥！请在.env文件中配置DOUBAO_API_KEY、OPENAI_API_KEY或GOOGLE_API_KEY")


# 当前使用的模型配置 - 延迟初始化
current_model_config = None

def get_current_config():
    """获取当前模型配置，支持延迟初始化"""
    global current_model_config
    if current_model_config is None:
        current_model_config = get_current_model_config()
    return current_model_config
