from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用程序配置设置"""

    # API Keys - 至少配置一个，优先级：豆包 > OpenAI > Gemini
    doubao_api_key: Optional[str] = None  # 豆包API密钥（推荐）
    openai_api_key: Optional[str] = None  # OpenAI API密钥
    google_api_key: Optional[str] = None  # Google Gemini API密钥
    anthropic_api_key: Optional[str] = None  # Anthropic Claude API密钥

    # 应用配置
    debug: bool = True
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # LLM配置
    default_model: str = "gpt-4o-mini"  # OpenAI模型名称（当使用OpenAI时）
    max_tokens: int = 1000
    temperature: float = 0.8

    # 豆包特定配置
    doubao_model: str = "doubao-seed-1-6-flash-250715"  # 豆包推理接入点ID
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"

    # Supabase 配置
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    database_url: Optional[str] = None

    class Config:
        env_file = [".env"]
        case_sensitive = False


# 全局设置实例
settings = Settings()
