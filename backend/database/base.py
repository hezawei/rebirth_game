# backend/database/base.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.logging_config import LOGGER
from config.settings import settings

# 【核心修改】从 settings 读取新的 DATABASE_URL
DATABASE_URL = settings.database_url or "sqlite:///./rebirth_game.db"  # 保留SQLite作为fallback

# 创建数据库引擎
if DATABASE_URL.startswith("postgresql"):
    # PostgreSQL 不需要 connect_args
    engine = create_engine(DATABASE_URL)
else:
    # SQLite 需要 connect_args
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI的依赖注入函数，提供数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库，创建所有表"""
    try:
        LOGGER.info("正在初始化数据库...")
        Base.metadata.create_all(bind=engine)
        LOGGER.info("数据库初始化成功，所有表已创建。")
    except Exception as e:
        LOGGER.error(f"数据库初始化失败: {e}")
        raise
