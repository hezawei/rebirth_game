from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class ChoiceOption(BaseModel):
    """故事分支选项及其影响描述"""

    option: str = Field(..., description="选项文本，控制在15字以内")
    summary: str = Field(..., description="该选择会带来的即时剧情走向概述")
    success_rate_delta: Optional[int] = Field(
        default=None, ge=-100, le=100, description="对主线成功率的增减值，可为负。设为None以隐藏数值。"
    )
    risk_level: Optional[str] = Field(
        default=None, description="风险等级：low / medium / high"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="与该选择相关的主题标签"
    )


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
    choices: List[ChoiceOption] = Field(..., description="AI生成的2-3个选项")
    image_url: str = Field(..., description="场景图片的URL路径")
    success_rate: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="主线任务成功率（0-100），由AI生成"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="额外的元数据，如生成时间、模型信息、分支信息等"
    )

class StorySegment(BaseModel):
    """故事片段响应"""
    session_id: int = Field(..., description="游戏会话ID")
    node_id: int = Field(..., description="此片段对应的节点ID")
    text: str = Field(..., description="AI生成的故事文本")
    choices: List[ChoiceOption] = Field(..., description="AI生成的2-3个选项")
    image_url: str = Field(..., description="场景图片的URL路径")
    success_rate: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="主线任务成功率（0-100）"
    )
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


# --- 新增：愿望敏感词校验与二阶段启动 ---

class WishCheckRequest(BaseModel):
    """敏感词校验请求"""
    wish: str = Field(..., description="用户的重生愿望")


class WishCheckResponse(BaseModel):
    """敏感词校验结果"""
    ok: bool = Field(..., description="是否通过校验")
    reason: Optional[str] = Field(None, description="不通过的原因")
    category: Optional[str] = Field(None, description="触发的敏感分类")


class PrepareStartRequest(BaseModel):
    """关卡元信息准备请求（不创建会话）"""
    wish: str = Field(..., description="用户的重生愿望")


class PrepareStartResponse(BaseModel):
    """关卡元信息响应"""
    level_title: str = Field(..., description="关卡标题")
    background: str = Field(..., description="关卡背景设定")
    main_quest: str = Field(..., description="主线任务")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元信息")


# --- 存档相关模型 ---


class StorySaveCreate(BaseModel):
    session_id: int = Field(..., description="会话ID")
    node_id: int = Field(..., description="要存档的节点ID")
    title: str = Field(..., min_length=1, max_length=100, description="存档标题")


class StorySaveUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="新的存档标题")
    status: Optional[Literal["active", "completed", "failed"]] = Field(
        None, description="新的存档状态"
    )


class StorySaveSummary(BaseModel):
    id: int
    session_id: int
    node_id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StorySaveDetail(StorySaveSummary):
    node: StorySegment


# --- 愿望审核记录 ---


class WishModerationRecordResponse(BaseModel):
    id: int
    wish_text: str
    status: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


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
    choices: List[ChoiceOption]
    chapter_number: int # 假设元数据中有章节号

    class Config:
        from_attributes = True

class GameSessionDetail(GameSessionSummary):
    """单个游戏会话的完整历史记录"""
    nodes: List[StoryNodeDetail]
