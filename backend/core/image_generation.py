"""
图像生成客户端
支持多种图像生成提供商的统一接口
"""

import json
import requests
from typing import Dict, Any, Optional, List
from config.logging_config import LOGGER
from config.settings import settings


class ImageGenerationError(Exception):
    """图像生成相关错误"""
    pass


class UniversalImageClient:
    """统一的图像生成客户端"""

    def __init__(self):
        self.current_provider = settings.image_provider
        self.config = self._get_current_config()
        LOGGER.info(f"图像生成客户端初始化完成，使用提供商: {self.current_provider}")

    def _get_current_config(self) -> Dict[str, Any]:
        """获取当前图像生成提供商的配置"""
        provider_config = settings.IMAGE_PROVIDERS.get(self.current_provider)
        if not provider_config:
            available = list(settings.IMAGE_PROVIDERS.keys())
            raise ValueError(f"未知的图像提供商: '{self.current_provider}'。可用的提供商: {available}")
        
        # 检查 API key 是否存在
        if not provider_config.get("api_key"):
            raise ValueError(f"图像提供商 '{self.current_provider}' 缺少 API key")
        
        return provider_config

    def generate_image(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        生成图像
        
        Args:
            prompt: 图像生成提示词
            model: 指定使用的模型，如果为None则使用默认模型
            **kwargs: 其他参数
        
        Returns:
            str: 生成的图像URL或base64数据
        """
        try:
            if self.config["provider_type"] == "oneapi":
                return self._generate_oneapi(prompt, model, **kwargs)
            else:
                raise ImageGenerationError(f"不支持的图像提供商类型: {self.config['provider_type']}")
        
        except Exception as e:
            LOGGER.error(f"图像生成失败: {e}")
            raise ImageGenerationError(f"图像生成失败: {str(e)}")

    def _generate_oneapi(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """使用OneAPI兼容接口生成图像"""
        
        # 选择模型
        if model is None:
            model = self.config["default_model"]
        
        if model not in self.config["models"]:
            available_models = list(self.config["models"].keys())
            raise ImageGenerationError(f"模型 '{model}' 不可用。可用模型: {available_models}")
        
        model_config = self.config["models"][model]
        
        # 构建请求
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model_config["model_name"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Generate an image based on this prompt: {prompt}"
                        }
                    ]
                }
            ],
            "max_tokens": model_config.get("max_tokens", 4096),
            "temperature": model_config.get("temperature", 0.7)
        }
        
        # 添加额外参数
        for key, value in kwargs.items():
            if key in ["max_tokens", "temperature"]:
                data[key] = value
        
        LOGGER.info(f"发送图像生成请求，模型: {model}, 提示词: {prompt[:100]}...")
        
        max_retries = max(0, int(getattr(settings, "image_max_retries", 1)))
        connect_timeout = float(getattr(settings, "image_connect_timeout_seconds", 8.0))
        first_read_timeout = float(getattr(settings, "image_first_read_timeout_seconds", 60.0))
        retry_read_timeout = float(getattr(settings, "image_retry_read_timeout_seconds", 30.0))

        attempt = 0
        while True:
            attempt += 1
            try:
                current_read_timeout = first_read_timeout if attempt == 1 else retry_read_timeout
                response = requests.post(
                    self.config["base_url"],
                    headers=headers,
                    json=data,
                    timeout=(connect_timeout, current_read_timeout)
                )
                response.raise_for_status()

                result = response.json()
                LOGGER.info(
                    f"图像生成成功，响应长度: {len(str(result))} (attempt {attempt}/{max_retries + 1})"
                )

                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    return content
                raise ImageGenerationError("API响应格式异常：缺少图像数据")

            except requests.exceptions.RequestException as e:
                LOGGER.error(
                    f"图像生成请求失败 attempt={attempt}/{max_retries + 1}: {e}"
                )
                if attempt <= max_retries:
                    LOGGER.info("图像生成网络异常，准备自动重试一次...")
                    continue
                raise ImageGenerationError(f"网络请求失败: {str(e)}")
            except json.JSONDecodeError as e:
                LOGGER.error(f"图像生成响应解析失败: {e}")
                raise ImageGenerationError(f"响应解析失败: {str(e)}")

    def list_models(self) -> List[str]:
        """列出可用的图像生成模型"""
        return list(self.config["models"].keys())

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取指定模型的信息"""
        if model not in self.config["models"]:
            raise ImageGenerationError(f"模型 '{model}' 不存在")
        return self.config["models"][model]


# 全局图像生成客户端实例
image_client = UniversalImageClient()
