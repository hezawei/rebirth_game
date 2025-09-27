from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.logging_config import LOGGER
from config.settings import settings

# 【PostgreSQL Only】Require a DATABASE_URL and vendor must be postgresql
if not settings.database_url:
    raise RuntimeError("DATABASE_URL must be set and point to a PostgreSQL instance")
DATABASE_URL = settings.database_url

db_url_lower = DATABASE_URL.lower()
if db_url_lower.startswith("postgresql"):
    vendor = "postgresql"
else:
    vendor = "unknown"

expect = (settings.enforce_db_vendor or "postgresql").strip().lower()
if vendor != expect or vendor != "postgresql":
    raise RuntimeError(
        f"数据库厂商校验失败: 仅支持 PostgreSQL。enforce_db_vendor={expect}, 实际URL={DATABASE_URL} (解析厂商: {vendor})"
    )

LOGGER.info(f"数据库配置: vendor={vendor}, url={DATABASE_URL}")

# Create PostgreSQL engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
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
    """Deprecated: Alembic manages schema for PostgreSQL; no-op."""
    return
