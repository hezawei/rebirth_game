# backend/database/crud.py
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from . import models
from backend.schemas import user as user_schema
from backend.core import security
from schemas.story import RawStoryData
from config.logging_config import LOGGER  # 导入日志
from typing import Optional, List
import uuid

# ===== 认证相关的 CRUD 函数 =====

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """根据邮箱地址获取用户"""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: user_schema.UserCreate) -> models.User:
    """创建新用户，包含密码哈希"""
    hashed_password = security.get_password_hash(user.password)
    # 使用 email 的一部分作为默认 nickname
    default_nickname = user.email.split('@')[0]
    db_user = models.User(
        email=user.email, 
        hashed_password=hashed_password,
        nickname=default_nickname
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    LOGGER.info(f"创建新用户: {user.email}")
    return db_user

# ===== 游戏流程相关的 CRUD 函数 =====

def create_game_session(db: Session, wish: str, user_id: str) -> models.GameSession:
    db_session = models.GameSession(wish=wish, user_id=user_id)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def create_story_node(db: Session, session_id: int, segment: RawStoryData, parent_id: int = None, user_choice: str = None) -> models.StoryNode:
    # 【新增逻辑】验证父节点
    if parent_id:
        parent_node = db.query(models.StoryNode).filter(
            models.StoryNode.id == parent_id,
            models.StoryNode.session_id == session_id
        ).first()
        if not parent_node:
            LOGGER.error(f"尝试创建节点时，找不到有效的父节点。Session ID: {session_id}, Parent ID: {parent_id}")
            # 在开发阶段，直接抛出异常而不是返回None
            raise ValueError(f"父节点 (id={parent_id}) 不存在或不属于会话 (session_id={session_id})")

    db_node = models.StoryNode(
        session_id=session_id,
        parent_id=parent_id,
        story_text=segment.text,
        image_url=segment.image_url,
        user_choice=user_choice
    )
    db_node.set_choices(segment.choices)
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node

def get_session_by_id(db: Session, session_id: int) -> models.GameSession:
    """根据ID获取游戏会话"""
    return db.query(models.GameSession).filter(models.GameSession.id == session_id).first()

def get_session_history(db: Session, session_id: int) -> List[models.StoryNode]:
    return db.query(models.StoryNode).filter(models.StoryNode.session_id == session_id).order_by(models.StoryNode.created_at).all()

def get_node_by_id(db: Session, node_id: int) -> models.StoryNode:
    """根据ID获取单个故事节点"""
    return db.query(models.StoryNode).filter(models.StoryNode.id == node_id).first()

def calculate_chapter_number(db: Session, session_id: int, node_id: int) -> int:
    """
    计算指定节点在其故事中的章节号

    Args:
        db: 数据库会话
        session_id: 游戏会话ID
        node_id: 节点ID

    Returns:
        int: 章节号（从1开始）
    """
    # 获取该会话的所有节点，按创建时间排序
    nodes = db.query(models.StoryNode).filter(
        models.StoryNode.session_id == session_id
    ).order_by(models.StoryNode.created_at).all()

    # 找到目标节点在列表中的位置
    for i, node in enumerate(nodes):
        if node.id == node_id:
            return i + 1  # 章节号从1开始

    # 如果没找到，返回1（默认值）
    LOGGER.warning(f"无法找到节点 {node_id} 在会话 {session_id} 中的位置，返回默认章节号1")
    return 1

def get_latest_node_by_session(db: Session, session_id: int, user_id: str) -> Optional[models.StoryNode]:
    """获取指定会话的最新节点，并验证所有权"""
    session = db.query(models.GameSession).filter(
        models.GameSession.id == session_id,
        models.GameSession.user_id == user_id
    ).first()
    
    if not session:
        return None # Session doesn't exist or doesn't belong to the user

    return db.query(models.StoryNode).filter(
        models.StoryNode.session_id == session_id
    ).order_by(models.StoryNode.created_at.desc()).first()

# 【核心修改】重命名并重写此函数
def prune_story_after_node(db: Session, node_id: int) -> models.StoryNode:
    """
    从指定节点之后开始修剪故事树（删除此节点的所有后代）。
    这是实现「在哪一章重来，就停在哪一章」的核心。

    Args:
        db: 数据库会话
        node_id: 玩家希望重新做选择的那个节点ID

    Returns:
        target_node: 目标节点本身，其后代已被清除。
    """
    target_node = get_node_by_id(db, node_id)

    if not target_node:
        LOGGER.error(f"尝试回溯时找不到目标节点: {node_id}")
        raise ValueError(f"节点 (id={node_id}) 不存在")

    LOGGER.info(f"正在从节点 {target_node.id} 之后进行时空回溯...")

    # 查找并记录所有需要删除的后代节点ID
    descendant_ids = []
    nodes_to_visit = list(target_node.children)
    while nodes_to_visit:
        current_node = nodes_to_visit.pop()
        descendant_ids.append(current_node.id)
        nodes_to_visit.extend(current_node.children)

    if descendant_ids:
        LOGGER.info(f"节点 {target_node.id} 的所有后代节点 {descendant_ids} 将被删除。")
        # 批量删除所有后代节点
        # 注意：由于 cascade 设置，理论上直接清空 children 也可以，但为了日志清晰和逻辑明确，我们先查找再删除。
        # 这里我们直接删除 target_node 的直接子节点，级联删除会处理孙子节点。
        for child in list(target_node.children):
            db.delete(child)
    else:
        LOGGER.info(f"节点 {target_node.id} 没有后代，无需删除。")

    db.commit()

    # 刷新目标节点的状态，确保其 'children' 集合为空
    db.refresh(target_node)

    LOGGER.info(f"已成功完成回溯，当前故事线的终点为节点 {target_node.id}。")
    return target_node

# ===== 用户资料相关的 CRUD 函数 =====

def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
    """根据ID获取用户"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user_profile(db: Session, user_id: str, nickname: Optional[str] = None,
                       age: Optional[int] = None, identity: Optional[str] = None,
                       photo_url: Optional[str] = None) -> Optional[models.User]:
    """更新用户资料"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    if nickname is not None:
        user.nickname = nickname
    if age is not None:
        user.age = age
    if identity is not None:
        user.identity = identity
    if photo_url is not None:
        user.photo_url = photo_url

    db.commit()
    db.refresh(user)
    LOGGER.info(f"更新用户资料: {user_id}")
    return user

# ===== 重生编年史相关的 CRUD 函数 =====

def get_sessions_by_user(db: Session, user_id: str) -> List[models.GameSession]:
    """获取指定用户的所有游戏会话，按时间倒序排列"""
    return db.query(models.GameSession).filter(models.GameSession.user_id == user_id).order_by(models.GameSession.created_at.desc()).all()

def get_session_details(db: Session, session_id: int, user_id: str) -> Optional[models.GameSession]:
    """
    获取单个游戏会话的详细信息，包括所有故事节点。
    同时验证该会话是否属于当前用户。
    """
    return db.query(models.GameSession).filter(
        models.GameSession.id == session_id,
        models.GameSession.user_id == user_id
    ).first()
