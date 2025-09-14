# backend/database/models.py
# 【新增导入】
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, DATABASE_URL
import json
import uuid

# 根据数据库类型选择UUID字段类型
def get_uuid_column():
    if DATABASE_URL.startswith("postgresql"):
        return UUID(as_uuid=True)
    else:
        # SQLite使用String存储UUID
        return String(36)

# 【新增】User 模型
class User(Base):
    __tablename__ = "users"

    id = Column(get_uuid_column(), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # 保留个人信息字段，设为可选
    nickname = Column(String(50), nullable=True)
    age = Column(Integer, nullable=True)
    identity = Column(String(100), nullable=True)
    photo_url = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

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
    )

    def get_choices(self) -> list:
        return json.loads(self.choices)

    def set_choices(self, choices: list):
        self.choices = json.dumps(choices)
