# backend/api/user.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database.base import get_db
from database import crud
from schemas.user import UserProfileCreate, UserProfileUpdate, UserProfile
from config.logging_config import LOGGER
from typing import Optional
import jwt
from config.settings import settings

router = APIRouter(prefix="/users", tags=["users"])

def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """从JWT token中提取用户ID"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证token")
    
    token = authorization.split(" ")[1]
    try:
        # 这里应该验证Supabase JWT，暂时简化处理
        # 在实际部署时需要使用Supabase的公钥验证JWT
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="无效的token")
        return user_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的token")

@router.post("/profile", response_model=UserProfile)
async def create_or_update_profile(
    profile_data: UserProfileCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """创建或更新用户资料"""
    try:
        # 检查用户是否已存在
        existing_user = crud.get_user_by_id(db, user_id)
        
        if existing_user:
            # 更新现有用户
            updated_user = crud.update_user_profile(
                db, user_id,
                nickname=profile_data.nickname,
                age=profile_data.age,
                identity=profile_data.identity,
                photo_url=profile_data.photo_url
            )
            return updated_user
        else:
            # 创建新用户
            new_user = crud.create_user(
                db, user_id,
                nickname=profile_data.nickname,
                age=profile_data.age,
                identity=profile_data.identity,
                photo_url=profile_data.photo_url
            )
            return new_user
            
    except Exception as e:
        LOGGER.error(f"创建/更新用户资料失败: {e}")
        raise HTTPException(status_code=500, detail="创建/更新用户资料失败")

@router.get("/profile", response_model=UserProfile)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取当前用户的资料"""
    try:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"获取用户资料失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户资料失败")
