"""
图像存储服务
负责将AI生成的图像下载并持久化到本地，确保图片的长期可用性
"""

import os
import hashlib
import requests
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse
from config.logging_config import LOGGER
from config.settings import settings


class ImageStorageService:
    """图像存储服务类"""
    
    def __init__(self):
        # 定义存储目录
        self.storage_dir = settings.BASE_DIR / "assets" / "generated_images"
        # 【关键修复】使用完整的后端URL而不是相对路径
        self.backend_base_url = f"http://{settings.backend_host}:{settings.backend_port}"
        self.web_path_prefix = f"{self.backend_base_url}/static/generated"
        
        # 确保存储目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        LOGGER.info(f"图像存储服务初始化完成，存储目录: {self.storage_dir}")
        LOGGER.info(f"图像web访问前缀: {self.web_path_prefix}")
    
    def save_ai_image(self, image_url: str, story_context: str) -> Optional[str]:
        """
        下载并保存AI生成的图像到本地
        
        Args:
            image_url: AI生成的图像URL
            story_context: 故事上下文，用于生成文件名
        
        Returns:
            本地图像的web访问路径，失败返回None
        """
        
        if not self._is_external_url(image_url):
            # 如果已经是本地URL，直接返回
            LOGGER.debug(f"图像已经是本地路径: {image_url}")
            return image_url
        
        try:
            LOGGER.info(f"开始下载AI图像: {image_url}")
            
            # 生成唯一的文件名
            filename = self._generate_filename(image_url, story_context)
            local_path = self.storage_dir / filename
            
            # 检查文件是否已存在（避免重复下载）
            if local_path.exists():
                web_url = f"{self.web_path_prefix}/{filename}"
                LOGGER.info(f"图像已存在，直接返回: {filename}")
                LOGGER.info(f"[图像访问URL]: {web_url}")
                return web_url
            
            # 下载图像
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                LOGGER.warning(f"URL返回的不是图像内容: {content_type}")
                return None
            
            # 保存到本地
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 强制刷新文件缓存，确保文件立即可访问
            try:
                with open(local_path, 'rb') as f:
                    f.flush()
                    os.fsync(f.fileno())
            except:
                pass  # 如果刷新失败也继续
            
            LOGGER.info(f"✅ 图像下载成功: {filename} (大小: {local_path.stat().st_size} 字节)")
            
            # 返回完整的web访问路径
            web_url = f"{self.web_path_prefix}/{filename}"
            LOGGER.info(f"[图像访问URL]: {web_url}")
            LOGGER.info(f"[本地文件路径]: {local_path}")
            return web_url
            
        except Exception as e:
            LOGGER.error(f"❌ 图像下载失败: {e}")
            return None
    
    
    def _is_external_url(self, url: str) -> bool:
        """判断是否为外部URL"""
        return url.startswith('http://') or url.startswith('https://')
    
    def _generate_filename(self, image_url: str, story_context: str) -> str:
        """
        生成唯一的文件名
        使用URL和故事上下文的哈希值，确保相同内容不重复存储
        """
        
        # 创建唯一标识符
        unique_string = f"{image_url}_{story_context[:100]}"
        hash_object = hashlib.md5(unique_string.encode())
        hash_hex = hash_object.hexdigest()
        
        # 尝试从URL获取文件扩展名
        parsed_url = urlparse(image_url)
        path = parsed_url.path.lower()
        
        if path.endswith('.png'):
            extension = '.png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            extension = '.jpg'
        elif path.endswith('.gif'):
            extension = '.gif'
        elif path.endswith('.webp'):
            extension = '.webp'
        else:
            extension = '.png'  # 默认使用PNG
        
        return f"ai_gen_{hash_hex}{extension}"
    
    def cleanup_old_images(self, days_old: int = 30) -> int:
        """
        清理超过指定天数的图像文件（可选的维护功能）
        
        Args:
            days_old: 超过多少天的文件被认为是旧文件
        
        Returns:
            删除的文件数量
        """
        
        import time
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        deleted_count = 0
        
        try:
            for file_path in self.storage_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    LOGGER.debug(f"删除旧图像文件: {file_path.name}")
            
            LOGGER.info(f"图像清理完成，删除了 {deleted_count} 个超过 {days_old} 天的文件")
            return deleted_count
            
        except Exception as e:
            LOGGER.error(f"图像清理失败: {e}")
            return 0
    
    def get_storage_stats(self) -> dict:
        """获取存储统计信息"""
        try:
            files = list(self.storage_dir.iterdir())
            total_files = len([f for f in files if f.is_file()])
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_dir": str(self.storage_dir)
            }
        except Exception as e:
            LOGGER.error(f"获取存储统计失败: {e}")
            return {"error": str(e)}


# 全局图像存储服务实例
image_storage = ImageStorageService()
