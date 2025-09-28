# backend/database/models.py
# 【新增导入】
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    CheckConstraint,
    UniqueConstraint,
    Boolean,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, DATABASE_URL
from config.logging_config import LOGGER
import json
import uuid

# 根据数据库类型选择UUID字段类型
def get_uuid_column():
    if DATABASE_URL.startswith("postgresql"):
        return UUID(as_uuid=True)
    else:
        # SQLite使用String存储UUID
        return String(36)

# 为不同数据库选择合适的默认值生成器
def get_uuid_default():
    if DATABASE_URL.startswith("postgresql"):
        # PostgreSQL 的 UUID 列应返回 uuid.UUID 对象
        return uuid.uuid4
    else:
        # 其他数据库（例如SQLite）使用字符串表示
        return lambda: str(uuid.uuid4())

# 【新增】User 模型
class User(Base):
    __tablename__ = "users"

    id = Column(get_uuid_column(), primary_key=True, default=get_uuid_default())
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # 保留个人信息字段，设为可选
    nickname = Column(String(50), nullable=True)
    age = Column(Integer, nullable=True)
    identity = Column(String(100), nullable=True)
    photo_url = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    # 单点登录版本号：每次登录自增，旧token全部失效
    token_version = Column(Integer, nullable=False, server_default='0')

    game_sessions = relationship("GameSession", back_populates="user")

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # 【核心修改】将 nullable 从 True 改为 False，强制所有新游戏都必须有关联用户
    user_id = Column(
        get_uuid_column(),
        ForeignKey("users.id"),
        nullable=False,  # 【从 True 改为 False】强制新数据的正确性
        index=True
    )
    wish = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="game_sessions")
    story_nodes = relationship("StoryNode", back_populates="session", cascade="all, delete-orphan")
    saves = relationship("StorySave", back_populates="session", cascade="all, delete-orphan")


class StoryNode(Base):
    __tablename__ = "story_nodes"

    id = Column(Integer, primary_key=True, index=True)
    # 【新增】为 session_id 和 parent_id 增加索引以提高查询性能
    session_id = Column(Integer, ForeignKey("game_sessions.id"), index=True)
    parent_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=True, index=True) # 指向上一个节点
    
    story_text = Column(Text, nullable=False)
    image_url = Column(String, nullable=False)
    choices = Column(Text, nullable=False) # 以JSON字符串形式储存
    user_choice = Column(String, nullable=True) # 从父节点到此节点的选择
    node_metadata = Column("metadata", JSON, nullable=False, default=dict)
    success_rate = Column(Integer, nullable=True)
    is_speculative = Column(Boolean, nullable=False, default=False)
    speculative_depth = Column(Integer, nullable=True)
    speculative_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("GameSession", back_populates="story_nodes")

    # 【核心修正】将'children'和'parent'的back_populates修正为正确的对应关系
    # 'children'关系应该反向填充到子节点的'parent'属性
    children = relationship("StoryNode", back_populates="parent", cascade="all, delete-orphan")

    # 'parent'关系应该反向填充到父节点的'children'属性
    parent = relationship("StoryNode", remote_side=[id], back_populates="children")

    # 【新增】表级别的约束
    __table_args__ = (
        CheckConstraint('parent_id != id', name='check_no_self_parent'),
        # 防止同一父节点下同一选择被重复创建（并发/重复点击保护）
        UniqueConstraint('session_id', 'parent_id', 'user_choice', name='uq_storynode_parent_choice'),
    )

    def get_choices(self) -> list:
        try:
            data = json.loads(self.choices)
            if isinstance(data, list):
                return data
        except Exception as exc:
            LOGGER.warning(f"无法解析节点 {self.id} 的 choices 字段: {exc}")
            return []

    def set_choices(self, choices: list):
        serialized = []
        for item in choices or []:
            if hasattr(item, "model_dump"):
                serialized.append(item.model_dump())
            elif isinstance(item, dict):
                serialized.append(item)
            else:
                serialized.append({"option": str(item)})
        self.choices = json.dumps(serialized, ensure_ascii=False)

    def get_metadata(self) -> dict:
        raw = self.node_metadata
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}

    def set_metadata(self, metadata: dict):
        if metadata is None:
            metadata = {}
        self.node_metadata = metadata


class StorySave(Base):
    __tablename__ = "story_saves"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("story_nodes.id"), nullable=False)
    title = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    session = relationship("GameSession", back_populates="saves")
    node = relationship("StoryNode")


class WishModerationRecord(Base):
    __tablename__ = "wish_moderation_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(get_uuid_column(), ForeignKey("users.id"), nullable=True, index=True)
    wish_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # passed / rejected
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
