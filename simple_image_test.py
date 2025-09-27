#!/usr/bin/env python3
"""
简单独立的图像生成测试脚本
包含所有配置，直接调用API，适合Linux服务器测试
"""

import requests
import json
import time
from typing import Optional


class SimpleImageClient:
    """简单的图像生成客户端"""
    
    def __init__(self):
        # 直接在代码中定义配置，方便测试
        self.config = {
            "api_key": "sk-peEyD4oWvXLCcCo2QM76UyAiMUBxiP2XAPYv3Q5VbsYfDmFd",
            "base_url": "https://oneapi.cyberclaude.com/v1/chat/completions",
            "models": {
                "qwen-image": "qwen-image",
                "nano-banana": "nano-banana"
            },
            "timeout": 60,  # 60秒超时
            "max_tokens": 4096,
            "temperature": 0.7
        }
        print(f"✅ 图像生成客户端初始化完成")
        print(f"📡 API URL: {self.config['base_url']}")
        print(f"🔑 API Key: {self.config['api_key'][:20]}...")
    
    def generate_image(self, prompt: str, model: str = "nano-banana") -> Optional[str]:
        """
        生成图像 - 最简单的实现
        
        Args:
            prompt: 图像描述
            model: 模型名称 (qwen-image 或 nano-banana)
        
        Returns:
            生成的图像URL或描述，失败返回None
        """
        
        # 输入验证
        if not prompt or not prompt.strip():
            print("❌ 错误: 提示词不能为空")
            return None
        
        if model not in self.config["models"]:
            print(f"❌ 错误: 模型 '{model}' 不支持，支持的模型: {list(self.config['models'].keys())}")
            return None
        
        print(f"\n🔄 开始生成图像...")
        print(f"📝 提示词: {prompt}")
        print(f"🎯 模型: {model}")
        
        # 构建请求
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config["models"][model],
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
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"]
        }
        
        try:
            # 发送请求
            print("📡 发送API请求...")
            start_time = time.time()
            
            response = requests.post(
                self.config["base_url"],
                headers=headers,
                json=payload,
                timeout=self.config["timeout"]
            )
            
            elapsed_time = time.time() - start_time
            print(f"⏱️  请求耗时: {elapsed_time:.2f}秒")
            
            # 检查HTTP状态
            if response.status_code != 200:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"📄 响应内容: {response.text[:500]}...")
                return None
            
            # 解析响应
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"📄 原始响应: {response.text[:500]}...")
                return None
            
            # 提取图像信息
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                
                print("✅ 图像生成成功!")
                print(f"📊 响应大小: {len(response.text)} 字符")
                print(f"📝 完整响应: {content}")
                
                return content
            else:
                print("❌ 响应格式异常: 缺少choices字段")
                print(f"📄 完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ 请求超时 ({self.config['timeout']}秒)")
            return None
        except requests.exceptions.ConnectionError:
            print("❌ 网络连接错误")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求异常: {e}")
            return None
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            return None


def test_basic_generation():
    """基础生成测试"""
    print("=" * 60)
    print("🧪 基础图像生成测试")
    print("=" * 60)
    
    client = SimpleImageClient()
    
    # 测试用例
    test_cases = [
        ("nano-banana", "A beautiful sunset over mountains"),
        ("nano-banana", "一只可爱的小猫咪"),
        ("qwen-image", "Future city with flying cars") if "qwen-image" in client.config["models"] else None
    ]
    
    # 过滤None
    test_cases = [case for case in test_cases if case is not None]
    
    success_count = 0
    for i, (model, prompt) in enumerate(test_cases, 1):
        print(f"\n📋 测试 {i}/{len(test_cases)}")
        print("-" * 40)
        
        result = client.generate_image(prompt, model)
        
        if result:
            print(f"✅ 测试 {i} 成功")
            success_count += 1
            
            # 尝试提取图像URL
            if "http" in result:
                import re
                urls = re.findall(r'https?://[^\s\)]+', result)
                if urls:
                    print(f"🖼️  图像URL: {urls[0]}")
        else:
            print(f"❌ 测试 {i} 失败")
    
    print(f"\n📊 测试结果: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)


def test_error_handling():
    """错误处理测试"""
    print("\n" + "=" * 60)
    print("🧪 错误处理测试")
    print("=" * 60)
    
    client = SimpleImageClient()
    
    error_tests = [
        ("空提示词", "", "nano-banana"),
        ("无效模型", "test prompt", "invalid-model"),
        ("超长提示词", "很长的提示词 " * 1000, "nano-banana")
    ]
    
    for test_name, prompt, model in error_tests:
        print(f"\n🔍 测试: {test_name}")
        print("-" * 30)
        
        result = client.generate_image(prompt, model)
        
        if result is None:
            print(f"✅ 正确处理了错误情况")
        else:
            print(f"⚠️  意外成功: {result[:100]}...")


def test_performance():
    """性能测试"""
    print("\n" + "=" * 60)
    print("🧪 性能测试")
    print("=" * 60)
    
    client = SimpleImageClient()
    
    # 简单的性能测试
    prompt = "A simple test image"
    model = "nano-banana"
    
    print(f"⏱️  测试图像生成速度...")
    
    start_time = time.time()
    result = client.generate_image(prompt, model)
    end_time = time.time()
    
    if result:
        print(f"✅ 性能测试完成")
        print(f"⏱️  总耗时: {end_time - start_time:.2f}秒")
        
        # 估算每分钟能生成多少图像
        images_per_minute = 60 / (end_time - start_time)
        print(f"📈 估算速度: {images_per_minute:.1f} 图像/分钟")
    else:
        print(f"❌ 性能测试失败")


def main():
    """主测试函数"""
    print("🚀 简单图像生成测试开始")
    print(f"⏰ 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🖥️  Python版本: {__import__('sys').version}")
    
    tests = [
        ("基础生成", test_basic_generation),
        ("错误处理", test_error_handling),
        ("性能测试", test_performance)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 开始 {test_name} 测试...")
            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except KeyboardInterrupt:
            print(f"\n⚠️  用户中断了 {test_name} 测试")
            break
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print("📊 最终结果")
    print("=" * 60)
    print(f"通过测试: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 所有测试通过! 图像生成功能正常")
    else:
        print("😞 部分测试失败，请检查配置和网络")
    
    # 输出使用说明
    print("\n💡 使用示例:")
    print("```python")
    print("client = SimpleImageClient()")
    print('result = client.generate_image("一只可爱的小猫", "nano-banana")')
    print("print(result)")
    print("```")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        import traceback
        traceback.print_exc()
