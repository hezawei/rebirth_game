#!/usr/bin/env python3
"""
图像生成功能测试脚本
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault('PYTHONPATH', str(project_root))

from backend.core.image_generation import image_client, ImageGenerationError
from config.logging_config import LOGGER


def test_list_models():
    """测试列出可用模型"""
    print("=" * 50)
    print("测试: 列出可用的图像生成模型")
    print("=" * 50)
    
    try:
        models = image_client.list_models()
        print(f"可用模型: {models}")
        
        for model in models:
            info = image_client.get_model_info(model)
            print(f"模型 {model} 配置: {info}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_image_generation():
    """测试图像生成功能"""
    print("\n" + "=" * 50)
    print("测试: 图像生成")
    print("=" * 50)
    
    test_prompts = [
        "A beautiful sunset over mountains",
        "一只可爱的小猫咪在花园里玩耍",
        "Future city with flying cars",
    ]
    
    models_to_test = image_client.list_models()
    
    for model in models_to_test:
        print(f"\n🔄 测试模型: {model}")
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n  测试 {i}: 提示词 = '{prompt}'")
            
            try:
                result = image_client.generate_image(
                    prompt=prompt,
                    model=model,
                    max_tokens=2048  # 降低token限制以节省成本
                )
                
                print(f"  ✅ 生成成功!")
                print(f"  📝 结果预览: {str(result)[:200]}...")
                
                if len(str(result)) > 200:
                    print(f"  📏 完整结果长度: {len(str(result))} 字符")
                
            except ImageGenerationError as e:
                print(f"  ❌ 生成失败: {e}")
                return False
            except Exception as e:
                print(f"  ❌ 未知错误: {e}")
                return False
    
    return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 50)
    print("测试: 错误处理")
    print("=" * 50)
    
    # 测试无效模型
    print("🔄 测试无效模型...")
    try:
        image_client.generate_image("test prompt", model="invalid-model")
        print("❌ 应该抛出错误但没有")
        return False
    except ImageGenerationError:
        print("✅ 正确处理了无效模型错误")
    except Exception as e:
        print(f"❌ 错误类型不正确: {e}")
        return False
    
    # 测试空提示词
    print("\n🔄 测试空提示词...")
    try:
        result = image_client.generate_image("")
        print(f"⚠️  空提示词生成结果: {str(result)[:100]}...")
    except Exception as e:
        print(f"⚠️  空提示词错误: {e}")
    
    return True


def main():
    """主测试函数"""
    print("🚀 开始图像生成功能测试")
    print(f"📁 项目根目录: {project_root}")
    print(f"🔧 当前图像提供商: {image_client.current_provider}")
    
    tests = [
        ("列出模型", test_list_models),
        ("图像生成", test_image_generation),
        ("错误处理", test_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 开始测试: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            LOGGER.error(f"测试 {test_name} 异常", exc_info=True)
    
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("😞 有测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
