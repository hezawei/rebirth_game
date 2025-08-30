"""
故事相关的API端点
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict
from schemas.story import StoryStartRequest, StoryContinueRequest, StorySegment, ErrorResponse, StoryRetryRequest
from core.story_engine import story_engine
from config.logging_config import LOGGER
from database.base import get_db
from database import crud, models
# 【新增导入】
from .user import get_current_user_id

# 创建路由器
router = APIRouter()


@router.post("/start", response_model=StorySegment)
async def start_new_story(
    request: StoryStartRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    开始新的重生故事

    Args:
        request: 包含用户重生愿望的请求
        db: 数据库会话
        user_id: 从JWT获取的当前用户ID

    Returns:
        StorySegment: 包含故事文本、选择选项和图片的响应
    """
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
    # 【核心修改】使用从JWT获取的user_id
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
    result = StorySegment(
        session_id=session.id,
        node_id=node.id,
        text=raw_data.text,
        choices=raw_data.choices,
        image_url=raw_data.image_url,
        metadata=metadata
    )

    LOGGER.info("新故事生成成功")
    return result


@router.post("/continue", response_model=StorySegment)
async def continue_existing_story(request: StoryContinueRequest, db: Session = Depends(get_db)):
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
    result = StorySegment(
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
@router.post("/retry", response_model=StorySegment)
async def retry_from_node(request: StoryRetryRequest, db: Session = Depends(get_db)):
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
        result = StorySegment(
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


@router.get("/sessions", response_model=List[Dict])
async def get_all_sessions(db: Session = Depends(get_db)):
    """获取所有游戏会话列表"""
    sessions = db.query(models.GameSession).order_by(models.GameSession.created_at.desc()).all()
    return [{"id": s.id, "wish": s.wish, "created_at": s.created_at} for s in sessions]

@router.get("/sessions/{session_id}", response_model=List[Dict])
async def get_session_details(session_id: int, db: Session = Depends(get_db)):
    """获取单个游戏会话的详细故事节点"""
    nodes = crud.get_session_history(db, session_id)  # 这里获取的已经是按时间排序的了
    result = []
    # 【核心修改】直接使用 enumerate 来生成章节号，无需再次计算
    for i, node in enumerate(nodes):
        result.append({
            "id": node.id,
            "text": node.story_text,
            "image_url": node.image_url,
            "user_choice": node.user_choice,
            "created_at": node.created_at,
            "chapter_number": i + 1,  # 直接使用索引+1作为章节号
            "choices": node.get_choices()  # 【新增这一行】
        })
    return result



@router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {"status": "healthy", "service": "story_api"}


# 注意：异常处理器应该在主应用中定义，不是在路由器中
