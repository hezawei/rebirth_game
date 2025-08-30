"""
结构化日志记录配置
使用loguru提供强大的日志功能
"""

import sys
from loguru import logger


def setup_logger():
    """
    设定一个全局的日志记录器
    """
    logger.remove()  # 移除预设的处理器
    
    # 输出到标准输出（控制台）
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 输出到文件
    logger.add(
        "rebirth_game.log",
        level="DEBUG",
        rotation="10 MB",  # 文件大小达到10MB时轮转
        retention="7 days",  # 最多保留7天的日志
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    return logger


# 全局日志实例
LOGGER = setup_logger()
