"""
大语言模型客户端封装
支持多种LLM供应商，便于未来切换
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from .model_config import get_current_config
from config.logging_config import LOGGER
from config.settings import settings
import time
import random
import threading
import httpx

# 动态导入，避免在不需要时报错
try:
    from volcenginesdkarkruntime import Ark
except ImportError:
    Ark = None

try:
    import openai
except ImportError:
    openai = None


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
        self.client: Any = None

        if self.model_config.provider_type == "doubao":
            if Ark is None:
                raise ImportError("豆包SDK未安装，请运行: pip install 'volcengine-python-sdk[ark]'")
            self.client = Ark(
                base_url=self.model_config.base_url,
                api_key=self.model_config.api_key,
                timeout=settings.llm_timeout_seconds
            )
            LOGGER.info(f"LLM客户端初始化成功 - 提供商: 豆包 (原生SDK)")
        
        elif self.model_config.provider_type == "openai":
            if openai is None:
                raise ImportError("OpenAI SDK未安装，请运行: pip install openai")
            
            client_params = self.model_config.get_client_params()
            default_headers = {
                "User-Agent": "PostmanRuntime/7.47.1",
                "Accept": "*/*",
                "Cache-Control": "no-cache",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
            client_params["default_headers"] = default_headers

            http_client = httpx.Client(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                # 增加读取超时，应对大文本生成时服务器响应慢的问题
                timeout=httpx.Timeout(settings.llm_timeout_seconds, connect=5.0, read=60.0)
            )
            client_params["http_client"] = http_client

            if settings.debug:
                loggable_params = {k: v for k, v in client_params.items() if k != 'http_client'}
                LOGGER.debug(f"[CLIENT PARAMS] {loggable_params}")
            
            self.client = openai.OpenAI(**client_params)
            LOGGER.info(f"LLM客户端初始化成功 - 提供商: OpenAI (兼容层)")
        
        else:
            raise ValueError(f"不支持的 provider_type: {self.model_config.provider_type}")

        LOGGER.info(f"模型: {self.model_config.model_name}")
        LOGGER.info(f"API地址: {self.model_config.base_url}")

        # 简单的运行期指标
        self._lock = threading.Lock()
        self.calls_total = 0
        self.retries_total = 0
        self.failures_total = 0
        self.total_latency_ms = 0.0
        self.last_latency_ms = 0.0
        self._latency_count = 0
        self.last_error: Optional[str] = None

    def generate(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_preamble_override: Optional[str] = None,
    ) -> str:
        """生成文本（支持按调用覆写模型/采样参数）"""
        messages: List[Dict[str, str]] = []

        # 预置系统提示：强制纯 JSON 输出
        system_preamble = (
            "你是一个专用于生成游戏剧情的AI，你的唯一任务是输出严格的JSON格式。\n"
            "# 绝对规则:\n"
            "1. **必须**只输出一个JSON对象，禁止任何JSON之外的文本、注释或Markdown标记。\n"
            "2. **必须**确保JSON语法完全正确，所有字符串都用双引号包裹，对象和数组正确闭合。\n"
            "3. **必须**包含以下所有字段，且类型完全匹配:\n"
            "   - `text`: (String) 故事的当前段落。\n"
            "   - `success_rate`: (Integer) 主线任务的成功率，范围0-100。\n"
            "   - `choices`: (Array) 一个包含3个选项对象的数组。如果故事自然结束，则返回一个空数组 `[]`。\n"
            "4. `choices`数组中的每个对象**必须**包含以下字段:\n"
            "   - `option`: (String) 玩家的选择项文本。\n"
            "   - `summary`: (String) 对该选项的简短描述。\n"
            "   - `success_rate_delta`: (Integer) 选择此项后，主线成功率的变化值，可以是正数、负数或0。\n"
            "# 完整示例:\n"
            "```json\n"
            "{\n"
            '  "text": "你站在分岔路口，左边是阴森的森林，右边是阳光明媚的小径。",\n'
            '  "success_rate": 50,\n'
            '  "choices": [\n'
            '    {\n'
            '      "option": "走进森林",\n'
            '      "summary": "充满未知危险，但可能藏有宝藏。",\n'
            '      "success_rate_delta": -10\n'
            '    },\n'
            '    {\n'
            '      "option": "踏上小径",\n'
            '      "summary": "看似安全，但可能平淡无奇。",\n'
            '      "success_rate_delta": 5\n'
            '    },\n'
            '    {\n'
            '      "option": "原地等待",\n'
            '      "summary": "也许会有其他人经过。",\n'
            '      "success_rate_delta": 0\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "```\n"
            "# 错误处理: 如果你因任何原因无法生成剧情，也**必须**返回一个结构合法的JSON，可在text字段中说明错误，例如: `{\"text\":\"内部错误，无法生成剧情。\", \"success_rate\":0, \"choices\":[]}`"
        )
        if system_preamble_override:
            system_preamble = system_preamble_override
        
        # 根据提供商构建 messages
        if self.model_config.provider_type == 'doubao':
            # 豆包原生SDK支持将 system prompt 放在第一条 user message 中
            messages = []
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": f"{system_preamble}\n\n{prompt}"})
        else: # openai
            messages = []
            messages.append({"role": "system", "content": system_preamble})
            if history:
                for message in history:
                    if isinstance(message, dict) and 'role' in message and 'content' in message:
                        messages.append(message)
                    elif isinstance(message, str):
                        messages.append({"role": "assistant", "content": message})
            messages.append({"role": "user", "content": prompt})

        # 获取模型特定的参数
        completion_params = self.model_config.get_completion_params()
        
        # JSON模式等参数已由 model_config 从 settings.py 中加载，此处无需额外处理
        # 覆写参数（若指定）
        if model is not None:
            completion_params["model"] = model
        if temperature is not None:
            completion_params["temperature"] = temperature
        if max_tokens is not None:
            completion_params["max_tokens"] = max_tokens
        completion_params["messages"] = messages

        # 动态构建并打印 curl 命令（可开关）
        if settings.llm_log_curl_enabled:
            try:
                curl_cmd = self._build_curl_command(completion_params)
                LOGGER.critical(f"[CURL COMMAND] {curl_cmd}")
            except Exception as e:
                LOGGER.error(f"构建 cURL 命令失败: {e}")

        max_tries = max(1, int(settings.llm_max_retries) + 1)
        backoff_min = max(0, int(settings.llm_retry_backoff_min_ms))
        backoff_max = max(backoff_min, int(settings.llm_retry_backoff_max_ms))

        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt < max_tries:
            attempt += 1
            start = time.perf_counter()
            try:
                # 根据客户端类型调用
                if self.model_config.provider_type == 'doubao':
                    # 豆包原生SDK调用
                    response = self.client.chat.completions.create(**completion_params)
                else: # openai
                    # OpenAI 兼容层调用，带 response_format 回退逻辑
                    try:
                        response = self.client.chat.completions.create(**completion_params)
                    except Exception as e:
                        has_rf = "response_format" in completion_params
                        msg = str(e)
                        if has_rf and ("response_format" in msg or "not support" in msg.lower() or "unsupported" in msg.lower()):
                            LOGGER.warning("代理可能不支持 response_format，正在移除该参数后重试（同一次尝试内）…")
                            retry_params = dict(completion_params)
                            retry_params.pop("response_format", None)
                            response = self.client.chat.completions.create(**retry_params)
                        else:
                            raise

                # 成功
                latency_ms = (time.perf_counter() - start) * 1000.0
                import json
                raw_content = response.choices[0].message.content

                # [终极修复] 应对 SiliconFlow 返回 "JSON in JSON" 的情况
                # 模型将我们要求的JSON对象，作为字符串塞进了它自己的content字段里
                if raw_content and raw_content.strip().startswith('{'):
                    try:
                        # 尝试将这个字符串再次解析为JSON对象
                        nested_json = json.loads(raw_content.strip())
                        # 如果成功，就将这个内部的JSON对象重新序列化为字符串返回
                        # 这确保了 story_engine 收到的是一个纯净的、它期望的JSON字符串
                        result = json.dumps(nested_json, ensure_ascii=False)
                        LOGGER.info("[JSON-in-JSON] 检测到并成功解析了嵌套的JSON响应。")
                    except json.JSONDecodeError:
                        # 如果再次解析失败，说明它不是一个完整的JSON，按原样返回
                        result = raw_content
                else:
                    # 如果不是以'{'开头，说明是普通文本，按原样返回
                    result = raw_content

                # 使用情况日志
                if hasattr(response, 'usage') and response.usage:
                    LOGGER.info(
                        f"模型生成成功 - 模型: {completion_params.get('model')}, tokens使用: {response.usage.total_tokens}"
                    )
                else:
                    LOGGER.info(f"模型生成成功 - 模型: {completion_params.get('model')}")

                # 指标更新
                with self._lock:
                    self.calls_total += 1
                    self.last_latency_ms = latency_ms
                    self.total_latency_ms += latency_ms
                    self._latency_count += 1
                    self.last_error = None

                # 尝试输出原始响应（仅 debug 模式）
                if settings.debug and hasattr(response, 'http_response') and hasattr(response.http_response, 'text'):
                    LOGGER.debug(f"[RAW RESPONSE] {response.http_response.text}")

                return result

            except Exception as e:
                last_exc = e
                # 最后一轮直接抛出
                if attempt >= max_tries:
                    with self._lock:
                        self.failures_total += 1
                        self.last_error = str(e)
                    raise

                # 退避等待后重试
                with self._lock:
                    self.retries_total += 1
                delay_ms = random.randint(backoff_min, backoff_max)
                time.sleep(delay_ms / 1000.0)

        # 理论上不会到达这里
        if last_exc:
            raise last_exc
        raise RuntimeError("LLM 调用失败（未知错误）")

    def get_metrics(self) -> Dict[str, object]:
        with self._lock:
            avg_latency_ms = (self.total_latency_ms / self._latency_count) if self._latency_count else None
            return {
                "model": self.model_config.model_name,
                "calls_total": self.calls_total,
                "retries_total": self.retries_total,
                "failures_total": self.failures_total,
                "last_latency_ms": round(self.last_latency_ms, 2) if self.last_latency_ms else None,
                "avg_latency_ms": round(avg_latency_ms, 2) if avg_latency_ms else None,
                "last_error": self.last_error,
                "timeout_seconds": settings.llm_timeout_seconds,
                "max_retries": settings.llm_max_retries,
            }

    def _build_curl_command(self, params: Dict) -> str:
        """根据请求参数动态构建一个可执行的 curl 命令字符串，并写入日志文件"""
        import json
        import os
        import shlex

        # 1. 获取基础 URL
        # 使用 shlex.quote 确保 URL 在 shell 命令中是安全的
        url = f"{str(self.client.base_url).strip('/')}/chat/completions"
        safe_url = shlex.quote(url)

        # 2. 构建请求头
        headers = self.client.default_headers.copy()
        # 掩码 API Key，避免日志泄漏敏感信息
        api_key = str(self.model_config.api_key or "")
        if len(api_key) > 8:
            masked = f"{api_key[:4]}...{api_key[-4:]}"
        else:
            masked = "****"
        headers["Authorization"] = f"Bearer {masked}"
        headers["Content-Type"] = "application/json"

        header_parts = []
        for key, value in headers.items():
            # 使用 -H 'Key: Value' 格式，这是 curl 的标准做法
            header_parts.append(f"-H {shlex.quote(f'{key}: {value}')}")
        
        header_str = ' '.join(header_parts)

        # 3. 构建请求体
        # 将 extra_body 的内容提升到顶层，这是OpenAI兼容API的通用做法
        request_body = params.copy()
        if 'extra_body' in request_body:
            extra = request_body.pop('extra_body')
            if isinstance(extra, dict):
                request_body.update(extra)

        # 使用 json.dumps 确保正确的 JSON 格式和转义
        # ensure_ascii=False 保证中文字符不被转义
        data_str = json.dumps(request_body, ensure_ascii=False)
        # 使用 shlex.quote 包装整个数据体，以处理特殊字符
        safe_data_str = shlex.quote(data_str)

        # 4. 组装最终命令
        # 使用 --data-raw 避免 shell 对数据内容进行额外处理
        curl_command = (
            f"curl --location {safe_url} "
            f"{header_str} "
            f"--data-raw {safe_data_str}"
        )
        
        # 5. 将 cURL 命令写入调试日志文件
        try:
            log_dir = os.path.join(settings.BASE_DIR, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, 'curl_debug.log')
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write("--- New Request ---\n")
                f.write(curl_command + "\n\n")
        except Exception as e:
            LOGGER.error(f"写入 cURL 调试日志失败: {e}")

        return curl_command


 # 全局客户端实例
llm_client = UniversalLLMClient()

def generate_text(prompt: str, history: Optional[List[Dict[str, str]]] = None, **kwargs) -> str:
    """统一便捷入口：返回字符串文本。可通过kwargs覆写 model/temperature/max_tokens。"""
    return llm_client.generate(prompt, history=history, **kwargs)
