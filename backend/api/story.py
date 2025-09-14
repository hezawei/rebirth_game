"""
故事相关的API端点
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict
# 【核心修正】导入整个schemas模块，而不仅仅是其中的类
from backend import schemas
from core.story_engine import story_engine
from config.logging_config import LOGGER
from database.base import get_db
from database import crud, models
# 导入新的安全依赖
from .user import get_current_user

# 创建路由器
router = APIRouter()


@router.post("/start", response_model=schemas.story.StorySegment)
async def start_new_story(
    request: schemas.story.StoryStartRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    开始新的重生故事 (需要认证)

    Args:
        request: 包含用户重生愿望的请求
        db: 数据库会话
        current_user: 从JWT获取的当前用户模型

    Returns:
        StorySegment: 包含故事文本、选择选项和图片的响应
    """
    user_id = current_user.id
    LOGGER.info(f"用户 {user_id} 收到新故事请求，愿望: {request.wish}")

    # 验证输入
    if not request.wish or len(request.wish.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重生愿望不能为空"
        )

    if len(request.wish) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重生愿望过长，请控制在100字以内"
        )

    # 1. 调用引擎生成第一段故事 (返回RawStoryData)
    raw_data = story_engine.start_story(wish=request.wish.strip())

    # 2. 创建游戏会话
    session = crud.create_game_session(db, wish=request.wish.strip(), user_id=user_id)

    # 3. 创建第一个故事节点
    node = crud.create_story_node(db, session_id=session.id, segment=raw_data)

    # 4. 【逻辑简化】开始故事永远是第1章
    chapter_number = 1

    # 5. 组合最终响应
    # 【核心修改】确保 metadata 结构一致
    metadata = {
        **(raw_data.metadata or {}),
        "chapter_number": chapter_number
    }
    result = schemas.story.StorySegment(
        session_id=session.id,
        node_id=node.id,
        text=raw_data.text,
        choices=raw_data.choices,
        image_url=raw_data.image_url,
        metadata=metadata
    )

    LOGGER.info("新故事生成成功")
    return result


@router.post("/continue", response_model=schemas.story.StorySegment)
async def continue_existing_story(request: schemas.story.StoryContinueRequest, db: Session = Depends(get_db)):
    """
    继续现有故事

    Args:
        request: 包含session_id、node_id和用户选择的请求
        db: 数据库会话

    Returns:
        StorySegment: 包含新故事文本、选择选项和图片的响应
    """
    LOGGER.info(f"收到故事继续请求，选择: {request.choice}")

    # 验证输入
    if not request.choice or len(request.choice.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户选择不能为空"
        )

    # 1. 从数据库获取故事历史 (转换为LLM需要的格式)
    nodes = crud.get_session_history(db, request.session_id)
    story_history = []
    for node in nodes:
        story_history.append({"role": "assistant", "content": node.story_text})
        if node.user_choice:
            story_history.append({"role": "user", "content": f"我选择了：{node.user_choice}"})

    # 2. 调用引擎生成下一段故事 (返回RawStoryData)
    raw_data = story_engine.continue_story(story_history, request.choice.strip())

    # 3. 创建新的故事节点
    new_node = crud.create_story_node(
        db,
        session_id=request.session_id,
        segment=raw_data,
        parent_id=request.node_id,
        user_choice=request.choice.strip()
    )

    # 4. 【核心修改】在这里调用一次 calculate_chapter_number 即可
    chapter_number = crud.calculate_chapter_number(db, request.session_id, new_node.id)

    # 5. 组合响应
    metadata = {
        **(raw_data.metadata or {}),
        "chapter_number": chapter_number
    }
    result = schemas.story.StorySegment(
        session_id=request.session_id,
        node_id=new_node.id,
        text=raw_data.text,
        choices=raw_data.choices,
        image_url=raw_data.image_url,
        metadata=metadata
    )

    LOGGER.info("故事继续生成成功")
    return result


# 【核心修改】修改 /retry 端点的函数签名和请求处理
@router.post("/retry", response_model=schemas.story.StorySegment)
async def retry_from_node(request: schemas.story.StoryRetryRequest, db: Session = Depends(get_db)):
    """
    从某个故事节点重新开始

    Args:
        request: 包含 "node_id" 的请求，node_id是玩家后悔的那个选择所产生的节点ID

    Returns:
        StorySegment: 玩家可以重新开始的那个父节点的完整信息
    """
    node_id = request.node_id  # 直接从验证过的模型中获取
    LOGGER.info(f"收到时空回溯请求，目标节点: {node_id}")

    try:
        # 【核心修改】调用新的 CRUD 函数
        target_node = crud.prune_story_after_node(db, node_id)

        # 计算回溯点的章节号
        chapter_number = crud.calculate_chapter_number(db, target_node.session_id, target_node.id)

        # 将返回的 SQLAlchemy 模型对象转换为 Pydantic 模型
        result = schemas.story.StorySegment(
            session_id=target_node.session_id,
            node_id=target_node.id,
            text=target_node.story_text,
            choices=target_node.get_choices(),
            image_url=target_node.image_url,
            metadata={"source": "retry", "chapter_number": chapter_number}
        )
        return result

    except ValueError as e:
        LOGGER.error(f"时空回溯失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        LOGGER.error(f"处理回溯请求时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="时空回溯时发生未知错误")


# --- 重生编年史 (Chronicle) API ---

@router.get("/sessions/{session_id}/latest", response_model=schemas.story.StorySegment)
async def get_latest_node_for_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取指定会话的最新节点以继续游戏 (需要认证)"""
    node = crud.get_latest_node_by_session(db, session_id=session_id, user_id=current_user.id)
    
    if not node:
        raise HTTPException(status_code=404, detail="找不到该游戏会话的最新节点，或该会话不属于你")

    chapter_number = crud.calculate_chapter_number(db, node.session_id, node.id)
    
    metadata = {
        "source": "continue",
        "chapter_number": chapter_number
    }
    
    return schemas.story.StorySegment(
        session_id=node.session_id,
        node_id=node.id,
        text=node.story_text,
        choices=node.get_choices(),
        image_url=node.image_url,
        metadata=metadata
    )

@router.get("/sessions", response_model=List[schemas.story.GameSessionSummary])
async def get_user_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取当前登录用户的所有游戏会话列表 (需要认证)"""
    sessions = crud.get_sessions_by_user(db, user_id=current_user.id)
    return sessions

@router.get("/sessions/{session_id}", response_model=schemas.story.GameSessionDetail)
async def get_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """获取单个游戏会话的详细历史 (需要认证)"""
    session = crud.get_session_details(db, session_id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="找不到该游戏会话，或该会话不属于你")

    # 手动构建响应模型，因为数据库模型和Pydantic模型结构不完全匹配
    nodes_details = []
    for i, node in enumerate(session.story_nodes):
        nodes_details.append(schemas.story.StoryNodeDetail(
            id=node.id,
            story_text=node.story_text,
            image_url=node.image_url,
            user_choice=node.user_choice,
            choices=node.get_choices(),
            chapter_number=i + 1
        ))

    return schemas.story.GameSessionDetail(
        id=session.id,
        wish=session.wish,
        created_at=session.created_at,
        nodes=nodes_details
    )



@router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {"status": "healthy", "service": "story_api"}


# 注意：异常处理器应该在主应用中定义，不是在路由器中
