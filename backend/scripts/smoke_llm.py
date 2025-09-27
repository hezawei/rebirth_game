"""
快速连通性测试脚本（OpenAI 兼容代理）

使用方式（在项目根目录执行）：
  python -m backend.scripts.smoke_llm --prompt "请返回一个包含text和choices键的JSON"

环境变量（.env 或系统环境）需配置：
  OPENAI_API_KEY=你的密钥
  OPENAI_BASE_URL=https://new.wuxuai.com/v1
  DEFAULT_MODEL=gemini-2.5-flash-lite-preview-06-17

可选：
  OPENAI_RESPONSE_FORMAT_JSON=false  # 建议先关闭（默认已关闭），避免与部分代理不兼容

注意：如果此前设置了 DOUBAO_API_KEY，请清空或移除，以确保选择 OpenAI 配置。
"""
from __future__ import annotations
import argparse
import os
import sys

# Add project root to the Python path
# This allows the script to be run from anywhere and still find the necessary modules.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from backend.core.llm_clients import generate_text
from config.settings import settings


def main():
    parser = argparse.ArgumentParser(description="LLM 代理连通性冒烟测试")
    parser.add_argument(
        "--prompt",
        type=str,
        default='请严格输出以下JSON：{"text": "你好，我已就绪", "choices": ["继续", "结束"]}',
        help="要发送给模型的提示词",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=settings.default_model,
        help="可覆盖 .env 中的 DEFAULT_MODEL",
    )
    args = parser.parse_args()

    print("--- 使用的配置 ---")
    print(f"BASE_URL     : {settings.openai_base_url or 'https://api.openai.com/v1'}")
    print(f"MODEL        : {args.model}")
    print(f"TEMP         : {settings.temperature}")
    print(f"MAX_TOKENS   : {settings.max_tokens}")

    print("\n--- 发送请求 ---")
    try:
        out = generate_text(
            args.prompt,
            model=args.model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
        print("\n--- 模型返回 ---")
        print(out)
    except Exception as e:
        print("调用失败：", e)
        raise


if __name__ == "__main__":
    main()
