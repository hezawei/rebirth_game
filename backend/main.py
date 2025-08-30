"""
FastAPI应用主入口
"""

import sys
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
backend_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_root))

# 导入新的日志系统
from config.logging_config import LOGGER
from api import story, user
from config.settings import settings

# 日志已在config/logging_config.py中配置

# 创建FastAPI应用
app = FastAPI(
    title="重生之我是…… API",
    description="一个基于AI的互动故事生成游戏后端服务",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件服务 - 直接指向images目录
images_path = project_root / "assets" / "images"
if images_path.exists():
    app.mount("/static", StaticFiles(directory=str(images_path)), name="static")
    LOGGER.info(f"静态文件服务已挂载到 /static 路径: {images_path}")
else:
    LOGGER.warning(f"静态文件目录不存在: {images_path}")

# 注册路由
app.include_router(story.router, prefix="/story", tags=["Story"])
app.include_router(user.router)

# 根路径
@app.get("/")
async def read_root():
    """根路径欢迎信息"""
    return {
        "message": "欢迎来到重生之我是……游戏API",
        "version": "0.1.0",
        "docs": "/docs" if settings.debug else "文档在生产环境中不可用",
        "status": "running"
    }

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    LOGGER.error(f"全局异常: {exc}")
    # 开发调试阶段：直接抛出异常，不做任何降级处理
    raise exc

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    # 初始化数据库
    from database.base import init_db
    init_db()

    LOGGER.info("重生之我是……API服务启动")
    LOGGER.info(f"调试模式: {settings.debug}")

    # 显示实际使用的模型
    from core.model_config import get_current_config
    current_config = get_current_config()
    LOGGER.info(f"当前使用模型: {current_config.model_name}")
    LOGGER.info(f"模型API地址: {current_config.base_url}")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    LOGGER.info("重生之我是……API服务关闭")

# 开发服务器启动
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    )
