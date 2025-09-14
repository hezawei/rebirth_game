from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class StoryStartRequest(BaseModel):
    """开始新故事的请求"""
    wish: str = Field(..., description="用户的重生愿望", example="中世纪骑士")


class StoryContinueRequest(BaseModel):
    """继续故事的请求"""
    session_id: int = Field(..., description="游戏会话ID")
    node_id: int = Field(..., description="当前节点ID")
    choice: str = Field(..., description="用户做出的选择")


class RawStoryData(BaseModel):
    """原始故事数据（从story_engine返回）"""
    text: str = Field(..., description="AI生成的故事文本")
    choices: List[str] = Field(..., description="AI生成的2-3个选项")
    image_url: str = Field(..., description="场景图片的URL路径")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="额外的元数据，如生成时间、模型信息等"
    )

class StorySegment(BaseModel):
    """故事片段响应"""
    session_id: int = Field(..., description="游戏会话ID")
    node_id: int = Field(..., description="此片段对应的节点ID")
    text: str = Field(..., description="AI生成的故事文本")
    choices: List[str] = Field(..., description="AI生成的2-3个选项")
    image_url: str = Field(..., description="场景图片的URL路径")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="额外的元数据，如生成时间、模型信息等"
    )


class StoryRetryRequest(BaseModel):
    """从指定节点重来的请求"""
    node_id: int = Field(..., description="玩家后悔的那个选择所产生的节点ID")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    code: Optional[str] = Field(None, description="错误代码")


# --- 重生编年史 (Chronicle) 相关模型 ---

class GameSessionSummary(BaseModel):
    """游戏会话的简要信息，用于列表展示"""
    id: int
    wish: str
    created_at: datetime

    class Config:
        from_attributes = True

class StoryNodeDetail(BaseModel):
    """故事节点的详细信息，用于展示历史记录"""
    id: int
    story_text: str
    image_url: str
    user_choice: Optional[str] = None
    choices: List[str] # 存储的是JSON字符串，需要解析
    chapter_number: int # 假设元数据中有章节号

    class Config:
        from_attributes = True

class GameSessionDetail(GameSessionSummary):
    """单个游戏会话的完整历史记录"""
    nodes: List[StoryNodeDetail]
