# backend/database/crud.py
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.core import security
from backend.schemas import user as user_schema
from config.logging_config import LOGGER  # 导入日志
from config.settings import settings
from schemas.story import RawStoryData

from . import models

# ===== 认证相关的 CRUD 函数 =====

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """根据邮箱地址获取用户（不区分大小写，忽略空白）"""
    normalized = (email or '').strip().lower()
    return db.query(models.User).filter(func.lower(models.User.email) == normalized).first()

def create_user(db: Session, user: user_schema.UserCreate) -> models.User:
    """创建新用户，包含密码哈希"""
    hashed_password = security.get_password_hash(user.password)
    normalized_email = user.email.strip().lower()
    # 使用 email 的一部分作为默认 nickname
    default_nickname = normalized_email.split('@')[0]
    db_user = models.User(
        email=normalized_email, 
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
    try:
        db.commit()
        db.refresh(db_session)
        return db_session
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(models.GameSession)
            .filter(models.GameSession.user_id == user_id, models.GameSession.wish == wish)
            .order_by(models.GameSession.id.desc())
            .first()
        )
        if existing:
            return existing
        raise

def create_story_node(
    db: Session,
    session_id: int,
    segment: RawStoryData,
    parent_id: int = None,
    user_choice: str = None,
    commit: bool = True,
    *,
    is_speculative: bool = False,
    speculative_depth: int | None = None,
    speculative_expires_at = None,
) -> models.StoryNode:
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
        user_choice=user_choice,
        success_rate=segment.success_rate,
        is_speculative=is_speculative,
        speculative_depth=speculative_depth,
        speculative_expires_at=speculative_expires_at,
    )
    db_node.set_choices(segment.choices)
    db_node.set_metadata(segment.metadata or {})
    db.add(db_node)
    if commit:
        db.commit()
        db.refresh(db_node)
    else:
        # 在调用方的事务里，仅刷新以便拿到自增ID；如违反唯一约束，将在flush时抛出IntegrityError
        db.flush()
        db.refresh(db_node)
    return db_node

def get_session_by_id(db: Session, session_id: int) -> models.GameSession:
    """根据ID获取游戏会话"""
    return db.query(models.GameSession).filter(models.GameSession.id == session_id).first()

def get_session_history(db: Session, session_id: int) -> List[models.StoryNode]:
    """获取指定会话的所有非预生成节点，按ID升序保证稳定顺序"""
    return (
        db.query(models.StoryNode)
        .filter(
            models.StoryNode.session_id == session_id,
            models.StoryNode.is_speculative.is_(False)
        )
        .order_by(models.StoryNode.id.asc())
        .all()
    )

def get_node_by_id(db: Session, node_id: int) -> models.StoryNode:
    """根据ID获取单个故事节点"""
    return db.query(models.StoryNode).filter(models.StoryNode.id == node_id).first()

def lock_node_for_update(db: Session, node_id: int) -> Optional[models.StoryNode]:
    """在支持的数据库上对节点加行级锁以避免并发写入竞争（PostgreSQL）。"""
    bind = db.get_bind()
    dialect = getattr(bind, "dialect", None)
    q = db.query(models.StoryNode).filter(models.StoryNode.id == node_id)
    if dialect and getattr(dialect, "name", "").lower() == "postgresql":
        q = q.with_for_update()
    return q.first()

def get_child_by_parent_and_choice(db: Session, session_id: int, parent_id: int, user_choice: str) -> Optional[models.StoryNode]:
    """获取同一父节点下，用户相同选择所产生的最新子节点（用于幂等/并发防抖）"""
    return (
        db.query(models.StoryNode)
        .filter(
            models.StoryNode.session_id == session_id,
            models.StoryNode.parent_id == parent_id,
            models.StoryNode.user_choice == user_choice,
        )
        .order_by(models.StoryNode.id.desc())
        .first()
    )


def get_children_for_parent(db: Session, parent_id: int, *, include_speculative: bool = True) -> List[models.StoryNode]:
    query = db.query(models.StoryNode).filter(models.StoryNode.parent_id == parent_id)
    if not include_speculative:
        query = query.filter(models.StoryNode.is_speculative.is_(False))
    return query.order_by(models.StoryNode.id.asc()).all()


def cleanup_expired_speculative_children(db: Session, parent_id: int) -> int:
    now = datetime.utcnow()
    q = (
        db.query(models.StoryNode)
        .filter(models.StoryNode.parent_id == parent_id)
        .filter(models.StoryNode.is_speculative.is_(True))
        .filter(models.StoryNode.speculative_expires_at.isnot(None))
        .filter(models.StoryNode.speculative_expires_at < now)
    )
    removed = q.delete(synchronize_session=False)
    if removed:
        db.commit()
    return removed


def finalize_speculative_node(db: Session, node: models.StoryNode, *, commit: bool = True) -> models.StoryNode:
    if not node.is_speculative:
        return node
    node.is_speculative = False
    node.speculative_depth = None
    node.speculative_expires_at = None
    if commit:
        db.commit()
        db.refresh(node)
    else:
        db.flush()
        db.refresh(node)
    return node


def update_story_node_from_segment(
    db: Session,
    node: models.StoryNode,
    segment: RawStoryData,
    *,
    commit: bool = True,
) -> models.StoryNode:
    node.story_text = segment.text
    node.image_url = segment.image_url
    node.success_rate = segment.success_rate
    node.set_choices(segment.choices)
    node.set_metadata(segment.metadata or {})
    if commit:
        db.commit()
        db.refresh(node)
    else:
        db.flush()
        db.refresh(node)
    return node

def calculate_chapter_number(db: Session, session_id: int, node_id: int) -> int:
    """
    计算指定节点在其故事中的章节号，基于从根节点到当前节点的路径深度

    Args:
        db: 数据库会话
        session_id: 游戏会话ID
        node_id: 节点ID

    Returns:
        int: 章节号（从1开始）
    """
    # 获取目标节点
    target_node = get_node_by_id(db, node_id)
    if not target_node or target_node.session_id != session_id:
        LOGGER.warning(f"节点 {node_id} 不存在或不属于会话 {session_id}")
        return 1
    
    # 从目标节点向上追溯到根节点，计算深度
    depth = 1
    current = target_node
    visited = set()
    
    while current.parent_id is not None:
        if current.id in visited:
            LOGGER.warning(f"检测到循环引用，节点 {current.id}")
            break
        visited.add(current.id)
        
        parent = get_node_by_id(db, current.parent_id)
        if not parent:
            break
        current = parent
        depth += 1
    
    return depth

def get_latest_node_by_session(db: Session, session_id: int, user_id: str) -> Optional[models.StoryNode]:
    """获取指定会话的最新节点，并验证所有权"""
    session = db.query(models.GameSession).filter(
        models.GameSession.id == session_id,
        models.GameSession.user_id == user_id
    ).first()
    
    if not session:
        return None # Session doesn't exist or doesn't belong to the user

    return (
        db.query(models.StoryNode)
        .filter(models.StoryNode.session_id == session_id)
        .order_by(models.StoryNode.id.desc())
        .first()
    )

def get_latest_node_for_user(db: Session, user_id: str) -> Optional[models.StoryNode]:
    """获取某个用户所有会话中的最新节点（按节点ID倒序作为时间的代理）"""
    return (
        db.query(models.StoryNode)
        .join(models.GameSession, models.StoryNode.session_id == models.GameSession.id)
        .filter(models.GameSession.user_id == user_id)
        .order_by(models.StoryNode.id.desc())
        .first()
    )

def get_deepest_node_for_user(db: Session, user_id: str) -> Optional[models.StoryNode]:
    """获取某个用户在所有会话中推进最深（章节数最多）的那个会话的最新节点。"""
    # 统计每个会话的节点数量，选择最多的那个会话
    sub = (
        db.query(models.StoryNode.session_id, func.count(models.StoryNode.id).label('cnt'))
        .join(models.GameSession, models.StoryNode.session_id == models.GameSession.id)
        .filter(models.GameSession.user_id == user_id)
        .group_by(models.StoryNode.session_id)
        .order_by(func.count(models.StoryNode.id).desc())
        .first()
    )
    if not sub:
        return None
    session_id = sub[0]

    # 返回该会话中的最新节点
    return (
        db.query(models.StoryNode)
        .filter(models.StoryNode.session_id == session_id)
        .order_by(models.StoryNode.id.desc())
        .first()
    )

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
    # 在支持的数据库上锁定目标节点，避免与并发的子节点创建竞争
    target_node = lock_node_for_update(db, node_id) or get_node_by_id(db, node_id)

    if not target_node:
        LOGGER.error(f"尝试回溯时找不到目标节点: {node_id}")
        raise ValueError(f"节点 (id={node_id}) 不存在")

    LOGGER.info(f"正在从节点 {target_node.id} 之后进行时空回溯...")

    # 遍历目标节点的所有子孙节点，统一标记为可复用的推演缓存，避免删除任何已生成内容
    descendants: list[models.StoryNode] = []
    stack = list(target_node.children)
    while stack:
        node = stack.pop()
        descendants.append(node)
        stack.extend(list(node.children))

    fallback_depth = max(0, getattr(settings, "speculation_max_depth", 0) - 1)
    for node in descendants:
        node.is_speculative = True
        node.speculative_depth = fallback_depth if fallback_depth > 0 else None
        node.speculative_expires_at = None

    db.commit()

    # 刷新目标节点的状态，确保其 'children' 集合指向最新数据
    db.refresh(target_node)

    if descendants:
        LOGGER.info(
            f"已完成回溯：保留并标记节点 {target_node.id} 的子孙节点 {[n.id for n in descendants]} 为推演缓存。"
        )
    else:
        LOGGER.info(f"已完成回溯：节点 {target_node.id} 无子孙节点需要处理。")

    return target_node

# ... (rest of the code remains the same)
    save = models.StorySave(session_id=session_id, node_id=node_id, title=title.strip(), status=status)
    db.add(save)
    db.commit()
    db.refresh(save)
    return save


def update_story_save(
    db: Session,
    save_id: int,
    *,
    title: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[models.StorySave]:
    save = db.query(models.StorySave).filter(models.StorySave.id == save_id).first()
    if not save:
        return None

    changed = False
    if title is not None and title.strip() and title.strip() != save.title:
        save.title = title.strip()
        changed = True
    if status is not None and status != save.status:
        save.status = status
        changed = True

    if changed:
        db.commit()
        db.refresh(save)
    return save


def get_story_save(db: Session, save_id: int, user_id: str) -> Optional[models.StorySave]:
    return (
        db.query(models.StorySave)
        .join(models.GameSession)
        .filter(models.StorySave.id == save_id, models.GameSession.user_id == user_id)
        .first()
    )


def list_story_saves(db: Session, user_id: str, status: str | None = None) -> List[models.StorySave]:
    query = (
        db.query(models.StorySave)
        .join(models.GameSession)
        .filter(models.GameSession.user_id == user_id)
        .order_by(models.StorySave.updated_at.desc())
    )
    if status:
        query = query.filter(models.StorySave.status == status)
    return query.all()


def delete_story_save(db: Session, save_id: int, user_id: str) -> bool:
    save = get_story_save(db, save_id, user_id)
    if not save:
        return False
    db.delete(save)
    db.commit()
    return True


# ===== 愿望审核记录 =====


def log_wish_moderation(db: Session, user_id: Optional[str], wish_text: str, status: str, reason: Optional[str] = None) -> models.WishModerationRecord:
    record = models.WishModerationRecord(user_id=user_id, wish_text=wish_text, status=status, reason=reason)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_wish_moderation_records(db: Session, user_id: str, limit: int = 50) -> List[models.WishModerationRecord]:
    return (
        db.query(models.WishModerationRecord)
        .filter(models.WishModerationRecord.user_id == user_id)
        .order_by(models.WishModerationRecord.created_at.desc())
        .limit(limit)
        .all()
    )

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
