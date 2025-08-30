#!/usr/bin/env python3
"""
项目快速设置脚本
"""

import os
import sys
import subprocess
from pathlib import Path
import urllib.request

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    print(f"✅ Python版本检查通过: {sys.version}")
    return True

def install_dependencies():
    """安装依赖"""
    print("📦 安装项目依赖...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败")
        return False

def setup_env_file():
    """设置环境变量文件"""
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env 文件已存在")
        return True
    
    print("📝 创建 .env 文件...")
    
    # 提示用户输入API密钥
    print("\n请提供以下配置信息（可稍后在.env文件中修改）:")
    
    openai_key = input("OpenAI API Key (可选，按回车跳过): ").strip()
    if not openai_key:
        openai_key = "your_openai_api_key_here"
    
    env_content = f"""# API Keys - 请填入你的API密钥
OPENAI_API_KEY="{openai_key}"
# ANTHROPIC_API_KEY="your_anthropic_api_key_here"
# GOOGLE_API_KEY="your_google_api_key_here"

# 应用配置
DEBUG=True
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
"""
    
    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)
        print("✅ .env 文件创建完成")
        return True
    except Exception as e:
        print(f"❌ .env 文件创建失败: {e}")
        return False

def download_placeholder_images():
    """下载占位符图片"""
    images_dir = Path("assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)
    
    placeholder_urls = [
        ("placeholder_01.png", "https://via.placeholder.com/800x400/667eea/ffffff?text=Fantasy+World"),
        ("placeholder_02.png", "https://via.placeholder.com/800x400/764ba2/ffffff?text=Sci-Fi+Future"),
        ("placeholder_03.png", "https://via.placeholder.com/800x400/f093fb/ffffff?text=Magic+Realm")
    ]
    
    print("🖼️  下载占位符图片...")
    
    for filename, url in placeholder_urls:
        filepath = images_dir / filename
        
        if filepath.exists():
            print(f"✅ {filename} 已存在")
            continue
        
        try:
            print(f"📥 下载 {filename}...")
            urllib.request.urlretrieve(url, filepath)
            print(f"✅ {filename} 下载完成")
        except Exception as e:
            print(f"⚠️  {filename} 下载失败: {e}")
            print(f"请手动下载或放置图片到: {filepath}")

def create_frontend_assets():
    """为前端创建资源副本"""
    frontend_assets = Path("frontend/assets")
    source_assets = Path("assets")
    
    if source_assets.exists():
        print("📁 为前端创建资源副本...")
        try:
            import shutil
            if frontend_assets.exists():
                shutil.rmtree(frontend_assets)
            shutil.copytree(source_assets, frontend_assets)
            print("✅ 前端资源副本创建完成")
        except Exception as e:
            print(f"⚠️  前端资源副本创建失败: {e}")

def main():
    """主设置流程"""
    print("🌟 重生之我是…… - 项目设置")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return
    
    # 安装依赖
    if not install_dependencies():
        return
    
    # 设置环境文件
    if not setup_env_file():
        return
    
    # 下载占位符图片
    download_placeholder_images()
    
    # 创建前端资源副本
    create_frontend_assets()
    
    print("\n" + "=" * 50)
    print("🎉 项目设置完成！")
    print("\n📋 下一步操作:")
    print("1. 编辑 .env 文件，填入你的 OpenAI API Key")
    print("2. 启动后端服务: python start_backend.py")
    print("3. 启动前端应用: python start_frontend.py")
    print("4. 在浏览器中访问: http://localhost:8501")
    print("\n📖 详细说明请查看 README.md")

if __name__ == "__main__":
    main()
