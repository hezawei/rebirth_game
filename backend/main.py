"""
FastAPI应用主入口
"""

import sys
import os
from pathlib import Path
from fastapi import FastAPI, Request, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import subprocess
from typing import List

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

# 带日志的静态文件服务，便于诊断是哪个挂载在处理请求
from fastapi.staticfiles import StaticFiles as _StaticFiles


class LoggedStaticFiles(_StaticFiles):
    """扩展 StaticFiles，记录服务命中与状态码，便于定位 404 来源"""

    def __init__(self, *args, label: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._label = label or "static"

    async def get_response(self, path, scope):  # type: ignore[override]
        LOGGER.debug(f"[Static:{self._label}] request path={path}")
        response = await super().get_response(path, scope)
        try:
            LOGGER.info(f"[Static:{self._label}] status={response.status_code} path={path}")
        except Exception:
            pass
        return response

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

# 先挂载 AI 生成图像目录到更具体的前缀，避免被 /static 吞掉
generated_images_path = project_root / "assets" / "generated_images"
generated_images_path.mkdir(parents=True, exist_ok=True)  # 确保目录存在
app.mount(
    "/static/generated",
    LoggedStaticFiles(directory=str(generated_images_path), html=True, label="generated"),
    name="generated_images",
)
LOGGER.info(
    f"AI生成图像服务已挂载到 /static/generated 路径: {generated_images_path} (热重载兼容模式)"
)
LOGGER.info(
    f"[静态文件服务] 后端完整访问地址示例: http://{settings.backend_host}:{settings.backend_port}/static/generated/xxx.png"
)

# 再挂载通用 /static 到预置图片目录（顺序很重要！）
images_path = project_root / "assets" / "images"
if images_path.exists():
    app.mount(
        "/static",
        LoggedStaticFiles(directory=str(images_path), label="images"),
        name="static",
    )
    LOGGER.info(f"静态文件服务已挂载到 /static 路径: {images_path}")
else:
    LOGGER.warning(f"静态文件目录不存在: {images_path}")

# 路由表调试：打印当前已挂载的所有路由（含顺序）
try:
    from starlette.routing import Mount
    for idx, r in enumerate(app.router.routes):
        try:
            r_type = r.__class__.__name__
            r_path = getattr(r, "path", "-")
            LOGGER.info(f"[RouteDump] #{idx} type={r_type} path={r_path}")
        except Exception:
            pass
except Exception:
    pass

# 静态请求探针：在进入具体静态应用前，记录将要访问的本地文件路径及存在性
@app.middleware("http")
async def _static_probe(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static/generated/"):
        filename = path.rsplit("/", 1)[-1]
        local_path = generated_images_path / filename
        exists = local_path.exists()
        size = local_path.stat().st_size if exists else 0
        LOGGER.info(f"[StaticProbe] generated hit path={path} -> {local_path} exists={exists} size={size}")
    elif path.startswith("/static/"):
        LOGGER.info(f"[StaticProbe] images hit path={path}")
    response = await call_next(request)
    return response

# 调试接口：列出 generated 目录下的文件
@app.get("/debug/static/generated/list")
async def debug_list_generated():
    try:
        files = []
        for p in sorted(generated_images_path.iterdir()):
            if p.is_file():
                files.append({
                    "name": p.name,
                    "size": p.stat().st_size,
                    "mtime": p.stat().st_mtime,
                })
        return {
            "dir": str(generated_images_path),
            "count": len(files),
            "files": files[-50:],  # 避免过长
        }
    except Exception as e:
        return {"error": str(e)}

# 调试接口：检查指定文件是否存在以及可读
@app.get("/debug/static/generated/check/{filename}")
async def debug_check_file(filename: str):
    from starlette.responses import FileResponse
    local_path = generated_images_path / filename
    exists = local_path.exists()
    size = local_path.stat().st_size if exists else 0
    LOGGER.info(f"[DebugCheck] {filename} exists={exists} size={size} path={local_path}")
    return {
        "exists": exists,
        "size": size,
        "path": str(local_path),
    }

# 注册路由
# 创建一个主API路由器，并添加 /api 前缀
api_router = APIRouter(prefix="/api")

# 将所有子路由器包含到主API路由器中
api_router.include_router(story.router, prefix="/story", tags=["Story"])
api_router.include_router(user.auth_router) # auth_router 已经有 /auth 前缀
api_router.include_router(user.profile_router) # profile_router 已经有 /users 前缀

# 将主API路由器包含到应用中
app.include_router(api_router)

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

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点，用于Docker健康检查和负载均衡"""
    try:
        # 检查数据库连接
        from sqlalchemy import create_engine, text
        from config.settings import settings
        
        if hasattr(settings, 'database_url') and settings.database_url:
            engine = create_engine(settings.database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
        else:
            db_status = "no_database_url"
            
        return {
            "status": "healthy",
            "database": db_status,
            "version": "0.1.0",
            "timestamp": str(os.path.getmtime(__file__))
        }
    except Exception as e:
        LOGGER.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "version": "0.1.0"
            }
        )

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    LOGGER.error(f"全局异常: {exc}")
    # 开发调试阶段：直接抛出异常，不做任何降级处理
    raise exc

# 启动事件
def _run_alembic_cmd(args: List[str]):
    try:
        cmd = [sys.executable, "-m", "alembic"] + list(args)
        LOGGER.info(f"Running Alembic: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=str(project_root), check=True)
        LOGGER.info("Alembic migration complete.")
    except Exception as e:
        LOGGER.error(f"Alembic migration failed: {e}")


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    # 先应用 Alembic 迁移，确保表和约束正确（跨平台统一）
    _run_alembic_cmd(["upgrade", "head"])

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
