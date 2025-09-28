# backend/api/user.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, Tuple

from backend.database import crud, models
from backend.database.base import get_db
from backend.schemas import user as user_schema
from backend.core import security
from config.logging_config import LOGGER
from config.settings import settings

# --- 认证相关的路由器 ---
auth_router = APIRouter(prefix="/auth", tags=["authentication"])

# --- 用户资料相关的路由器 ---
profile_router = APIRouter(prefix="/users", tags=["profiles"])

def _pick_token_from_request(request: Request) -> str:
    """
    Single auth path: HttpOnly cookie 'access_token'.
    Raise 401 if missing.
    """
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
    )


def _issue_access_token(response: Response, user: models.User) -> Tuple[str, int]:
    """Create JWT, write it into HttpOnly cookie, and return token plus expires_in (seconds)."""
    expires_minutes = getattr(settings, "access_token_expire_minutes", 60)
    expires_seconds = int(expires_minutes) * 60
    token_version = int(getattr(user, "token_version", 0) or 0)
    access_token = security.create_access_token(data={"sub": user.email, "ver": token_version})

    secure_flag = not bool(getattr(settings, "debug", False))
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=secure_flag,
        path="/",
        max_age=expires_seconds,
    )
    return access_token, expires_seconds

# --- 安全依赖 ---
async def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    """
    解码Token，验证用户，并返回用户模型实例
    这是一个可重用的依赖，用于保护需要认证的接口
    """
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无法验证凭证")
    
    token = _pick_token_from_request(request)
    token_data = security.decode_access_token(token)
    if token_data is None or not token_data.sub:
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=token_data.sub)
    if user is None:
        raise credentials_exception
    # 校验token版本，若不一致说明该账号已在其他地方登录，当前token失效
    if token_data.ver is None or user.token_version is None or int(token_data.ver) != int(user.token_version):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效：你的账号在其他位置登录，当前会话已登出")
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
    response: Response,
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
    
    # 单点登录：登录成功即自增 token_version，使旧token全部失效
    try:
        current_ver = int(getattr(user, 'token_version', 0) or 0)
    except Exception:
        current_ver = 0
    user.token_version = current_ver + 1
    db.add(user)
    db.commit()
    db.refresh(user)

    # 在token中加入版本号，并写入Cookie
    access_token, expires_seconds = _issue_access_token(response, user)
    return {"access_token": access_token, "token_type": "bearer", "expires_in": expires_seconds}


@auth_router.post("/refresh")
async def refresh_access_token(
    response: Response,
    current_user: models.User = Depends(get_current_user),
):
    """Refresh the HttpOnly access token cookie when the existing token is still valid."""
    LOGGER.info("用户 %s 发起令牌续期", current_user.email)
    access_token, expires_seconds = _issue_access_token(response, current_user)
    LOGGER.debug("续期成功: expires_in=%s", expires_seconds)
    return {"status": "success"}


@auth_router.post("/logout", status_code=204)
async def logout_current_user(
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """服务端登出：通过自增 token_version 使所有现有 token 立即失效。"""
    try:
        current_ver = int(getattr(current_user, 'token_version', 0) or 0)
    except Exception:
        current_ver = 0
    current_user.token_version = current_ver + 1
    db.add(current_user)
    db.commit()
    # Clear HttpOnly cookie
    response.delete_cookie("access_token", path="/")
    LOGGER.info(f"用户 {current_user.email} 已登出，token_version -> {current_user.token_version}")
    return

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
        created_at=current_user.created_at,
        roles=["user"]
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
