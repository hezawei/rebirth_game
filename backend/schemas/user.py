# backend/schemas/user.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserProfileCreate(BaseModel):
    """创建用户资料的请求模型"""
    nickname: str
    age: Optional[int] = None
    identity: Optional[str] = None
    photo_url: Optional[str] = None

class UserProfileUpdate(BaseModel):
    """更新用户资料的请求模型"""
    nickname: Optional[str] = None
    age: Optional[int] = None
    identity: Optional[str] = None
    photo_url: Optional[str] = None

class UserProfile(BaseModel):
    """用户资料响应模型"""
    id: str
    nickname: str
    age: Optional[int] = None
    identity: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
