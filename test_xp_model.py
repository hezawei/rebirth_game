#!/usr/bin/env python3
"""
小鹏公司内部豆包模型使用示例
最简单的文本请求和图片描述示例

使用前请确保：
1. 安装依赖：pip install aiohttp pillow
2. 替换API_KEY为你的实际密钥
3. 确保图片文件存在（如果测试图片描述功能）
"""

import asyncio
import aiohttp
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ===== 配置信息 =====
API_KEY = os.getenv("DOUBAO_API_KEY")
API_BASE = os.getenv("DOUBAO_BASE_URL")
MODEL = os.getenv("DOUBAO_MODEL")

def create_test_image(filename: str = "test_image.jpg") -> str:
    """
    创建一个简单的测试图片

    Args:
        filename: 图片文件名

    Returns:
        创建的图片文件路径
    """
    # 创建一个简单的彩色图片
    width, height = 400, 300
    image = Image.new('RGB', (width, height), color='lightblue')
    draw = ImageDraw.Draw(image)

    # 画一些简单的图形
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black', width=2)
    draw.ellipse([200, 50, 300, 150], fill='green', outline='black', width=2)
    draw.polygon([(100, 200), (150, 180), (200, 200), (175, 250), (125, 250)],
                 fill='yellow', outline='black')

    # 添加文字（使用默认字体）
    try:
        draw.text((50, 20), "Test Image", fill='black')
        draw.text((50, 270), "Red Square, Green Circle, Yellow Star", fill='black')
    except:
        # 如果字体有问题，跳过文字
        pass

    # 保存图片
    image.save(filename, 'JPEG')
    return filename

async def simple_text_request(question: str) -> str:
    """
    最简单的文本请求示例
    
    Args:
        question: 要问的问题
        
    Returns:
        回答
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # 关键：使用嵌套content数组格式，包含system和user消息
    payload = {
        'messages': [
            {
                'content': [
                    {
                        'text': '你是一个有用的AI助手，请提供准确、有帮助的回答。',
                        'type': 'text'
                    }
                ],
                "role": "system"
            },
            {
                'content': [
                    {
                        'text': question,
                        'type': 'text'
                    }
                ],
                "role": "user"
            }
        ],
        'model': MODEL,
        'stream': False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        ) as response:
            if response.status == 200:
                result = await response.json()
                # 标准OpenAI格式解析
                if "choices" in result and result["choices"]:
                    message = result["choices"][0]["message"]
                    return message.get("content", "无回答")
                else:
                    return f"响应格式异常: {result}"
            else:
                error_text = await response.text()
                return f"请求失败 {response.status}: {error_text}"

async def simple_image_description(image_path: str, prompt: str = "请详细描述这张图片") -> str:
    """
    最简单的图片描述示例
    
    Args:
        image_path: 图片文件路径
        prompt: 描述提示词
        
    Returns:
        图片描述结果
    """
    # 读取图片并转换为base64
    try:
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
    except FileNotFoundError:
        return f"图片文件不存在: {image_path}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # 关键：图片格式要与实际图片匹配（PNG用png，JPG用jpeg）
    image_format = "jpeg" if image_path.lower().endswith(('.jpg', '.jpeg')) else "png"
    
    payload = {
        'messages': [
            {
                'content': [
                    {
                        'text': '你是一个专业的图片分析助手',
                        'type': 'text'
                    }
                ],
                "role": "system"
            },
            {
                'content': [
                    {
                        'image_url': {
                            'url': f"image/{image_format};base64,{image_data}"
                        },
                        'type': 'image_url'
                    },
                    {
                        'text': prompt,
                        'type': 'text'
                    }
                ],
                "role": "user"
            }
        ],
        'model': MODEL,
        'temperature': 0.0,  # 只保留这三个基本参数
        'stream': False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120  # 图片处理需要更长时间
        ) as response:
            if response.status == 200:
                result = await response.json()
                # 标准OpenAI格式解析
                if "choices" in result and result["choices"]:
                    message = result["choices"][0]["message"]
                    return message.get("content", "无法获取图片描述")
                else:
                    return f"响应格式异常: {result}"
            else:
                error_text = await response.text()
                return f"请求失败 {response.status}: {error_text}"

async def main():
    """主函数：演示文本和图片请求"""
    print("🚀 小鹏豆包模型使用示例")
    print("=" * 50)
    
    # 示例1：文本请求
    print("📝 示例1：文本请求")
    text_result = await simple_text_request("你好，请简单介绍一下自己")
    print(f"回答: {text_result}")
    
    print("\n" + "=" * 50)
    
    # # 示例2：图片描述（自动生成测试图片）
    # print("📷 示例2：图片描述")

    # # 自动创建测试图片
    # print("🎨 正在创建测试图片...")
    # image_path = create_test_image("test_image.jpg")
    # print(f"✅ 测试图片已创建: {image_path}")

    # # 进行图片描述
    # image_result = await simple_image_description(image_path)
    # print(f"图片描述: {image_result}")

    # 清理临时文件（可选）
    # os.remove(image_path)  # 取消注释可自动删除测试图片

if __name__ == "__main__":
    asyncio.run(main())

"""
===== 重要注意事项和排雷指南 =====

🔥 关键成功要素：
1. 消息格式：必须使用嵌套content数组格式，包含system和user消息
2. 参数精简：只保留 model、temperature、stream 三个基本参数
3. 图片格式：image/格式要与实际图片格式匹配（jpeg/png）
4. 响应解析：使用标准OpenAI格式解析 result["choices"][0]["message"]["content"]

❌ 常见错误和解决方案：

1. "Ai模型开小差，请稍后重试！"
   - 原因：添加了额外参数（如thinking、top_p、max_tokens等）
   - 解决：只保留基本参数，移除所有额外参数

2. "响应格式异常"
   - 原因：图片格式不匹配（如PNG图片用了jpeg格式）
   - 解决：确保data:image/格式与实际图片格式一致

3. "请求失败"
   - 原因：API密钥错误或网络问题
   - 解决：检查API_KEY和网络连接

4. 图片描述失败
   - 原因：图片太大或格式不支持
   - 解决：压缩图片或转换为标准格式（JPG/PNG）

✅ 最佳实践：
- 文本请求：使用简单的system+user消息结构
- 图片请求：确保图片格式匹配，设置较长的timeout
- 错误处理：检查HTTP状态码和响应格式
- 并发处理：可以使用asyncio.gather()同时处理多个请求

🎯 性能优化：
- 豆包支持高并发，单个API密钥可以同时发送多个请求
- 图片描述自动启用thinking模式，无需额外配置
- 温度设置为0.0可获得更稳定的结果

📞 技术支持：
如遇到问题，请检查：
1. API密钥是否正确
2. 网络连接是否正常
3. 请求格式是否符合上述要求
4. 图片文件是否存在且格式正确
"""
