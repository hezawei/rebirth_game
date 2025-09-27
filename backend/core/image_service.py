"""
智能图片服务
实现混合图片策略：优先查库，失败后即时生成（预留接口）
"""

import os
import random
from typing import List, Optional
from config.logging_config import LOGGER
from pathlib import Path  # 【<<< 新增这一行导入】
from config.settings import settings, resolve_public_base_url

# 【新增】定义项目根目录
# __file__ 是当前文件的路径 -> .parent 是 core/ -> .parent 是 backend/ -> .parent 是 rebirth_game/
PROJECT_ROOT = Path(__file__).parent.parent.parent


class ImageService:
    """智能图片服务类"""
    
    def __init__(self, pregenerated_dir: str = "assets/images"):
        # self.pregenerated_dir = pregenerated_dir # 删除旧的写法
        self.pregenerated_dir = PROJECT_ROOT / pregenerated_dir  # 【<<< 使用新的写法】
        self.image_library = self._load_image_library()
        
        # 【新增】初始化后端URL前缀用于静态图片
        self.backend_base_url = resolve_public_base_url()

    def _load_image_library(self) -> List[str]:
        """从指定目录载入所有预置图片的路径，排除错误占位符"""
        if not os.path.exists(self.pregenerated_dir):
            LOGGER.warning(f"预置图片目录不存在: {self.pregenerated_dir}，将使用空图库")
            return []

        # 排除错误占位符和README文件
        excluded_files = {'error_placeholder.png', 'README.md'}
        images = [
            f for f in os.listdir(self.pregenerated_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f not in excluded_files
        ]
        LOGGER.info(f"成功从 '{self.pregenerated_dir}' 载入 {len(images)} 张预置图片（已排除错误占位符）")
        return images

    def get_random_image_from_library(self) -> str:
        """
        从图库中随机选择一张图片作为备用图片
        """
        LOGGER.info(f"[ImageLibrary] 从图库随机选择图片，图库大小: {len(self.image_library)}")

        base_url = resolve_public_base_url()

        if not self.image_library:
            LOGGER.error("[ImageLibrary] 图片库为空，返回错误占位符")
            return f"{base_url}/static/error_placeholder.png"

        # 直接随机选择，不做任何关键字匹配
        selected_image = random.choice(self.image_library)
        # 【关键修复】使用完整的后端URL
        result_url = f"{base_url}/static/{selected_image}"
        
        LOGGER.info(f"[ImageLibrary] ✅ 随机选择图片: {selected_image}")
        LOGGER.info(f"[ImageLibrary] 🎯 返回图片URL: {result_url}")
        return result_url

    def generate_image_realtime(self, story_text: str) -> str:
        """
        即时生成图片的接口
        使用AI模型根据故事文本生成图片，并保存到本地
        """
        LOGGER.info(f"[AIImageGen] 🚀 开始即时生成图片，故事文本长度: {len(story_text)}")
        
        try:
            # 导入图像生成客户端和存储服务（延迟导入避免循环依赖）
            LOGGER.debug("[AIImageGen] 导入图像生成客户端和存储服务...")
            from .image_generation import image_client
            from .image_storage import image_storage
            
            # 提取故事的关键元素作为提示词
            LOGGER.debug("[AIImageGen] 提取图像提示词...")
            prompt = self._extract_image_prompt(story_text)
            LOGGER.info(f"[AIImageGen] 📝 生成的图像提示词: {prompt[:100]}...")
            
            # 调用AI生成图像
            LOGGER.info("[AIImageGen] 🎨 调用AI生成图像中...")
            ai_result = image_client.generate_image(prompt)
            LOGGER.info(f"[AIImageGen] ✅ AI图像生成API调用成功，响应长度: {len(str(ai_result))}")
            
            # 从AI响应中提取图像URL
            LOGGER.debug("[AIImageGen] 提取图像URL...")
            image_url = self._extract_image_url(ai_result)
            
            if image_url:
                LOGGER.info(f"[AIImageGen] 🔗 提取到图像URL: {image_url}")
                
                # 下载并保存图像到本地
                LOGGER.info("[AIImageGen] 💾 开始下载并保存图像到本地...")
                local_path = image_storage.save_ai_image(image_url, story_text)
                
                if local_path:
                    LOGGER.info(f"[AIImageGen] ✅ 图像已完全保存并验证可访问: {local_path}")
                    return local_path
                else:
                    LOGGER.error("[AIImageGen] ❌ 图像保存或验证失败，降级到随机图库")
                    # 保存失败，立即降级到随机图库
                    return self.get_random_image_from_library()
            else:
                LOGGER.warning("[AIImageGen] ⚠️ 无法从AI响应中提取图像URL，降级到随机图库")
                return self.get_random_image_from_library()
            
        except Exception as e:
            LOGGER.error(f"[AIImageGen] ❌ 即时图片生成失败: {e}，降级到随机图库")
            # 失败时降级到随机图库
            return self.get_random_image_from_library()
    
    def _extract_image_url(self, ai_response: str) -> Optional[str]:
        """
        从AI响应中提取图像URL
        
        Args:
            ai_response: AI返回的原始响应
        
        Returns:
            提取出的图像URL，如果没找到则返回None
        """
        import re
        
        # 尝试匹配常见的图像URL模式
        url_patterns = [
            r'https?://[^\s\)]+\.(?:png|jpg|jpeg|gif|webp)',  # 直接的图片URL
            r'https?://[^\s\)]+',  # 任何HTTP URL
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, ai_response, re.IGNORECASE)
            if matches:
                url = matches[0]
                LOGGER.debug(f"从AI响应中提取到URL: {url}")
                return url
        
        LOGGER.warning(f"无法从AI响应中提取图像URL: {ai_response[:200]}...")
        return None
    
    def _extract_image_prompt(self, story_text: str) -> str:
        """
        从故事文本中提取适合生成图像的提示词
        """
        # 简单的提示词提取逻辑
        # 这里可以根据需要进一步优化，比如使用NLP技术提取关键词
        
        # 限制文本长度，避免提示词过长
        text = story_text[:500] if len(story_text) > 500 else story_text
        
        # 基本的图像生成提示词模板
        prompt = f"Create a cinematic and atmospheric image that captures the essence of this story scene: {text}. Style: detailed, dramatic lighting, high quality."
        
        return prompt

    def get_image_for_story(self, story_text: str) -> str:
        """
        获取故事图片的主函数
        
        Args:
            story_text: 故事文本
        
        逻辑：
        - 如果开关开启：优先AI生成 → 失败则随机本地图片
        - 如果开关关闭：直接随机本地图片
        """
        LOGGER.info(f"[ImageService] 🎨 开始为故事获取图片，故事文本长度: {len(story_text)}")
        
        if settings.enable_ai_image_generation:
            # 策略A：AI优先模式
            LOGGER.info("[ImageService] 🤖 AI图像生成已启用，优先尝试AI生成...")
            
            try:
                # 尝试AI生成图像
                ai_result = self.generate_image_realtime(story_text)
                # 检查是否是错误占位符（AI生成失败的标志）
                if ai_result and not ai_result.endswith("error_placeholder.png"):
                    LOGGER.info(f"[ImageService] ✅ AI生成成功: {ai_result}")
                    return ai_result
                else:
                    LOGGER.warning("[ImageService] ⚠️ AI生成返回错误占位符，降级到随机图库")
                    return self.get_random_image_from_library()
                
            except Exception as e:
                LOGGER.warning(f"[ImageService] ❌ AI图像生成失败: {e}")
                LOGGER.info("[ImageService] 🔄 降级到本地图库随机选择...")
                
                # AI失败，降级到本地随机图片
                return self.get_random_image_from_library()
        else:
            # 策略B：仅本地模式
            LOGGER.info("[ImageService] 📁 AI图像生成已禁用，直接使用本地图库...")
            return self.get_random_image_from_library()


# 全局图片服务实例
image_service = ImageService()
