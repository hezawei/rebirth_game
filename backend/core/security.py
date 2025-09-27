from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from config.settings import settings

# --- Password Hashing ---
# Use CryptContext for handling password hashing and verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码和哈希密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码的哈希值"""
    return pwd_context.hash(password)


# --- JSON Web Token (JWT) ---
# --- JSON Web Token (JWT) ---
# 配置现在从 config.settings 中加载，实现了统一管理
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

class TokenData(BaseModel):
    """Token中存储的数据模型"""
    sub: Optional[str] = None
    ver: Optional[int] = None  # 单点登录的token版本号

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    :param data: 需要编码到token中的数据 (通常是 {'sub': user_email})
    :param expires_delta: token的有效期，如果未提供则使用默认值
    :return: JWT字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[TokenData]:
    """
    解码并验证JWT
    :param token: JWT字符串
    :return: TokenData，包含主题sub与版本ver；验证失败返回None。
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: Optional[str] = payload.get("sub")
        version = payload.get("ver")
        if subject is None:
            return None
        return TokenData(sub=subject, ver=version)
    except JWTError:
        return None
