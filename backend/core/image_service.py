"""
智能图片服务
实现混合图片策略：优先查库，失败后即时生成（预留接口）
"""

import os
import random
from typing import List
from config.logging_config import LOGGER
from pathlib import Path  # 【<<< 新增这一行导入】

# 【新增】定义项目根目录
# __file__ 是当前文件的路径 -> .parent 是 core/ -> .parent 是 backend/ -> .parent 是 rebirth_game/
PROJECT_ROOT = Path(__file__).parent.parent.parent


class ImageService:
    """智能图片服务类"""
    
    def __init__(self, pregenerated_dir: str = "assets/images"):
        # self.pregenerated_dir = pregenerated_dir # 删除旧的写法
        self.pregenerated_dir = PROJECT_ROOT / pregenerated_dir  # 【<<< 使用新的写法】
        self.image_library = self._load_image_library()

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

    def find_image_in_library(self, story_text: str) -> str:
        """
        基于关键字的图片匹配实现
        根据故事文本中的关键字智能选择相关图片
        """
        LOGGER.info("正在从预置图库中查找图片...")

        if not self.image_library:
            LOGGER.error("图片库为空，无法提供图片！")
            return f"/error_placeholder.png"

        # 【核心修改】实现基于档名关键字的简易匹配
        keyword_map = {
            "森林": "forest", "魔法": "magic", "奇幻": "fantasy",
            "城堡": "castle", "城市": "city", "赛博": "cyberpunk",
            "空间": "space", "太空": "space", "星际": "space"
        }

        matched_images = []
        for keyword_cn, keyword_en in keyword_map.items():
            if keyword_cn in story_text:
                for img_file in self.image_library:
                    if keyword_en in img_file.lower():
                        matched_images.append(img_file)

        if matched_images:
            # 如果有匹配的图片，从匹配结果中随机选一张
            selected_image = random.choice(matched_images)
            LOGGER.info(f"根据关键字 '{story_text[:20]}...' 匹配到图片: {selected_image}")
        else:
            # 如果没有匹配，再从整个图库随机选
            selected_image = random.choice(self.image_library)
            LOGGER.info(f"未匹配到关键字，随机选择了图片: {selected_image}")

        return f"/{selected_image}"

    def generate_image_realtime(self, story_text: str) -> str:
        """
        即时生成图片的预留接口
        在当前阶段，此功能不实现，仅抛出一个错误
        """
        LOGGER.warning("触发了即时图片生成，但在阶段二中尚未实现")
        # 抛出未实现的错误，让我们在日志中清晰地看到这个问题
        raise NotImplementedError("即时图片生成功能尚未在阶段二中实现")

    def get_image_for_story(self, story_text: str) -> str:
        """
        获取故事图片的主函数（混合策略）
        """
        LOGGER.debug(f"开始为故事获取图片，故事文本长度: {len(story_text)}")
        
        # 步骤1：优先在图库中查找
        image_url = self.find_image_in_library(story_text)
        LOGGER.debug(f"图库查找结果: {image_url}")
        return image_url
        
        # 注意：根据开发调试阶段的要求，我们不做任何错误降级处理
        # 如果图库查找失败，直接让错误暴露出来
        # 步骤2的即时生成接口在当前阶段不启用


# 全局图片服务实例
image_service = ImageService()
