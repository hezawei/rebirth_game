# backend/api/user.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import crud, models
from backend.database.base import get_db
from backend.schemas import user as user_schema
from backend.core import security
from config.logging_config import LOGGER

# --- 认证相关的路由器 ---
auth_router = APIRouter(prefix="/auth", tags=["authentication"])

# --- 用户资料相关的路由器 ---
profile_router = APIRouter(prefix="/users", tags=["profiles"])

# OAuth2PasswordBearer 用于从请求头中提取Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- 安全依赖 ---
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    """
    解码Token，验证用户，并返回用户模型实例
    这是一个可重用的依赖，用于保护需要认证的接口
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    email = security.decode_access_token(token)
    if email is None:
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# --- 认证接口 ---

@auth_router.post("/register", response_model=user_schema.User)
async def register_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    """
    注册新用户
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    created_user = crud.create_user(db=db, user=user)
    return created_user

@auth_router.post("/token", response_model=user_schema.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    用户登录以获取访问令牌 (JWT)
    """
    user = crud.get_user_by_email(db, email=form_data.username) # form.username 对应的是 email
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- 用户资料接口 (现在受到保护) ---

@profile_router.get("/me", response_model=user_schema.UserProfile)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    获取当前登录用户的个人资料
    """
    # UserProfile schema 需要 email 字段，我们从 current_user 中获取
    return user_schema.UserProfile(
        id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
        age=current_user.age,
        identity=current_user.identity,
        photo_url=current_user.photo_url,
        created_at=current_user.created_at
    )

@profile_router.put("/me", response_model=user_schema.UserProfile)
async def update_current_user_profile(
    profile_data: user_schema.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    更新当前登录用户的个人资料
    """
    updated_user = crud.update_user_profile(
        db,
        user_id=current_user.id,
        nickname=profile_data.nickname,
        age=profile_data.age,
        identity=profile_data.identity,
        photo_url=profile_data.photo_url
    )
    if not updated_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return user_schema.UserProfile.from_orm(updated_user)
