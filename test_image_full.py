#!/usr/bin/env python3
"""
完整图像功能测试脚本
测试图像生成客户端和图像服务的集成
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
from backend.core.image_service import image_service
from config.logging_config import LOGGER
from config.settings import settings


def test_image_client():
    """测试底层图像生成客户端"""
    print("=" * 50)
    print("测试: 图像生成客户端")
    print("=" * 50)
    
    try:
        # 列出可用模型
        models = image_client.list_models()
        print(f"✅ 可用模型: {models}")
        
        # 测试简单的图像生成
        test_prompt = "A serene mountain landscape at sunset"
        print(f"🔄 测试提示词: '{test_prompt}'")
        
        result = image_client.generate_image(test_prompt)
        print(f"✅ 生成成功!")
        print(f"📝 结果: {str(result)[:200]}...")
        
        return True
    except Exception as e:
        print(f"❌ 客户端测试失败: {e}")
        LOGGER.error("图像客户端测试失败", exc_info=True)
        return False


def test_image_service_integration():
    """测试图像服务集成"""
    print("\n" + "=" * 50)
    print("测试: 图像服务集成")
    print("=" * 50)
    
    test_stories = [
        "在一个古老的城堡里，公主正在等待着她的王子。夕阳西下，城堡在金色的光芒中显得格外美丽。",
        "The brave knight rode through the enchanted forest, his armor gleaming in the moonlight.",
        "在未来的城市中，飞行汽车穿梭在摩天大楼之间，霓虹灯闪烁着各种颜色。"
    ]
    
    # 测试当前配置状态
    print(f"🔧 AI图像生成开关: {settings.enable_ai_image_generation}")
    print(f"🔧 当前图像提供商: {settings.image_provider}")
    
    # 测试1: 使用当前配置
    print("\n🧪 测试1: 使用当前配置")
    for i, story in enumerate(test_stories, 1):
        print(f"\n  故事 {i}: {story[:50]}...")
        try:
            result = image_service.get_image_for_story(story)
            print(f"  ✅ 结果: {result}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
    
    # 测试2: 临时开启AI生成测试
    print("\n🧪 测试2: 临时开启AI生成")
    original_setting = settings.enable_ai_image_generation
    try:
        settings.enable_ai_image_generation = True
        for i, story in enumerate(test_stories[:2], 1):  # 只测试前两个，节省资源
            print(f"\n  AI生成测试 {i}: {story[:50]}...")
            try:
                result = image_service.get_image_for_story(story)
                print(f"  ✅ AI生成结果: {result[:100]}...")
            except Exception as e:
                print(f"  ❌ AI生成失败: {e}")
    finally:
        settings.enable_ai_image_generation = original_setting
    
    return True


def test_configuration_toggle():
    """测试配置开关功能"""
    print("\n" + "=" * 50)
    print("测试: 配置开关功能")
    print("=" * 50)
    
    test_story = "A magical wizard casting spells in a mystical tower."
    
    # 保存原始配置
    original_setting = settings.enable_ai_image_generation
    
    try:
        # 测试关闭AI生成
        print("🔄 测试AI生成关闭状态...")
        settings.enable_ai_image_generation = False
        result_off = image_service.get_image_for_story(test_story)
        print(f"  AI关闭结果: {result_off}")
        
        # 测试开启AI生成
        print("\n🔄 测试AI生成开启状态...")
        settings.enable_ai_image_generation = True
        result_on = image_service.get_image_for_story(test_story)
        print(f"  AI开启结果: {result_on}")
        
        # 分析结果差异
        if result_off != result_on:
            print("✅ 配置开关工作正常，不同设置产生了不同结果")
        else:
            print("⚠️  配置开关可能没有按预期工作")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置开关测试失败: {e}")
        return False
    finally:
        # 恢复原始配置
        settings.enable_ai_image_generation = original_setting
        print(f"🔄 已恢复原始配置: enable_ai_image_generation = {original_setting}")


def test_error_scenarios():
    """测试错误场景"""
    print("\n" + "=" * 50)
    print("测试: 错误场景处理")
    print("=" * 50)
    
    # 测试空文本
    print("🔄 测试空文本...")
    try:
        result = image_service.get_image_for_story("")
        print(f"  空文本结果: {result}")
    except Exception as e:
        print(f"  空文本错误: {e}")
    
    # 测试极长文本
    print("\n🔄 测试极长文本...")
    long_text = "很长的故事文本 " * 1000
    try:
        result = image_service.get_image_for_story(long_text)
        print(f"  长文本结果: {result}")
    except Exception as e:
        print(f"  长文本错误: {e}")
    
    # 测试特殊字符
    print("\n🔄 测试特殊字符...")
    special_text = "故事包含特殊字符: @#$%^&*()_+{}|:<>?[]\\;'\",./"
    try:
        result = image_service.get_image_for_story(special_text)
        print(f"  特殊字符结果: {result}")
    except Exception as e:
        print(f"  特殊字符错误: {e}")
    
    return True


def main():
    """主测试函数"""
    print("🚀 开始完整图像功能测试")
    print(f"📁 项目根目录: {project_root}")
    print(f"🔧 当前配置:")
    print(f"   - 图像提供商: {settings.image_provider}")
    print(f"   - AI生成开关: {settings.enable_ai_image_generation}")
    
    tests = [
        ("图像生成客户端", test_image_client),
        ("图像服务集成", test_image_service_integration),
        ("配置开关功能", test_configuration_toggle),
        ("错误场景处理", test_error_scenarios),
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
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过!")
        print("\n💡 使用建议:")
        print("1. 在生产环境中，建议将 enable_ai_image_generation 设为 True")
        print("2. 可以通过修改 config/settings.py 切换不同的图像生成模型")
        print("3. 通过开关控制即可实现AI生成或本地图库的灵活切换")
        return 0
    else:
        print("😞 有测试失败")
        print("\n🔧 故障排除建议:")
        print("1. 检查网络连接和API密钥")
        print("2. 确认图像提供商配置正确")
        print("3. 查看详细日志定位问题")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
