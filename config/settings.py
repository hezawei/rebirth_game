import pathlib
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用程序配置设置"""

    # --- 项目路径 ---
    # 项目根目录 (rebirth_game)
    BASE_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent

    # 当前使用的LLM提供商（在 LLM_PROVIDERS 中的键名）
    llm_provider: str = "dashscope"
    
    # 当前使用的图像生成提供商（在 IMAGE_PROVIDERS 中的键名）
    image_provider: str = "openai"
    
    # 是否启用AI图像生成功能（如果为False，仅使用预置图库）
    enable_ai_image_generation: bool = True  # 可选: doubao / openai / dashscope

    # --- 统一模型配置 --- (新)
    LLM_PROVIDERS: dict = {
        "doubao": {
            "provider_type": "doubao",
            "api_key": "3fbb5f47-1c92-491b-a75b-e3cbda62a708",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "model": "doubao-seed-1-6-flash-250828",
            "completion_params": {
                "max_tokens": 5000,
                "temperature": 0.8,
                "response_format": {"type": "json_object"}
            }
        },
        "openai": {
            "provider_type": "openai",
            "api_key": "sk-wS5OgHlkuSl7DzRQ1UbuWp6acm2vmKxEp5uceO8oGP4ChdtC",
            "base_url": "https://new.wuxuai.com/v1",
            "model": "[自营]gemini-2.5-flash-preview-05-20",
            "completion_params": {
                "max_tokens": 5000,
                "temperature": 0.6,
                "response_format": {"type": "json_object"}
            }
        },
        "dashscope": {
            "provider_type": "openai", # 复用OpenAI客户端
            "api_key": "sk-e2eae7aa4d794271890b0772c963b102",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-flash-2025-07-28",
            "completion_params": {
                "max_tokens": 4096, # 平衡成本与生成长度
                "temperature": 0.75, # 鼓励创意，同时保持逻辑
                "response_format": {"type": "json_object"}, # 确保结构化输出
                "extra_body": {
                    "enable_thinking": False # 按要求关闭思考模式，适配非流式输出
                }
            }
        }
    }

    # --- 图像生成模型配置 ---
    IMAGE_PROVIDERS: dict = {
        "openai": {
            "provider_type": "oneapi",
            "api_key": "sk-peEyD4oWvXLCcCo2QM76UyAiMUBxiP2XAPYv3Q5VbsYfDmFd",
            "base_url": "https://oneapi.cyberclaude.com/v1/chat/completions",
            "models": {
                "qwen-image": {
                    "model_name": "qwen-image",
                    "max_tokens": 4096,
                    "temperature": 0.7
                },
                "nano-banana": {
                    "model_name": "nano-banana", 
                    "max_tokens": 4096,
                    "temperature": 0.7
                }
            },
            "default_model": "nano-banana"
        }
    }

    # --- 图像生成网络控制 ---
    image_connect_timeout_seconds: float = 8.0      # 连接超时（秒）
    image_first_read_timeout_seconds: float = 60.0  # 首次请求读取超时（秒）
    image_retry_read_timeout_seconds: float = 30.0  # 重试请求读取超时（秒）
    image_max_retries: int = 1                      # 最大重试次数（不含首发）

    # --- LLM 通用设置 ---
    openai_response_format_json: bool = True # 保留用于OpenAI兼容层的总开关
    # 超时与重试（单位：秒/次）
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_retry_backoff_min_ms: int = 250
    llm_retry_backoff_max_ms: int = 1000

    # --- 应用配置 ---
    app_title: str = "重生之我是……"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # --- 服务器配置 ---
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # 对外暴露的完整基础 URL（用于拼接静态资源绝对路径），未设置时回退到 backend_host/backend_port
    public_base_url: Optional[str] = None

    # --- ChapterFlow 配置参数 ---
    min_nodes: int = 6
    max_nodes: int = 22
    pass_threshold: int = 80
    fail_threshold: int = 90

    # --- 数据库 ---
    database_url: Optional[str] = "postgresql+psycopg2://rebirth:StrongPass!@127.0.0.1:5432/rebirth"
    enforce_db_vendor: Optional[str] = "postgresql"

    # --- 安全与认证 ---
    secret_key: str = "a_very_long_and_random_secret_key_for_jwt_32_bytes_long"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- 推演式剧情预生成 ---
    speculation_enabled: bool = True
    speculation_max_depth: int = 1
    speculation_max_workers: int = 60
    # 可选：每用户并发限制（目前仅指标展示，不强制）
    speculation_max_concurrency_per_user: int = 9
    # 单层最大新建节点数量上限（成本控制），建议 12~27 之间
    speculation_level_cap: int = 18
    # 单节点并发生成的最大 worker 数
    speculation_choice_workers: int = 9


    # --- 调试与日志 ---
    # 是否写入 cURL 调试日志；默认关闭，避免泄漏敏感信息
    llm_log_curl_enabled: bool = False

    class Config:
        # env_file = [".env"] # 禁用 .env 文件加载
        case_sensitive = False


# 全局设置实例
settings = Settings()


def resolve_public_base_url() -> str:
    """返回用于拼接静态资源绝对路径的基础 URL。"""
    base = settings.public_base_url
    if base:
        return base.rstrip('/')
    return f"http://{settings.backend_host}:{settings.backend_port}".rstrip('/')
