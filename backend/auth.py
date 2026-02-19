"""
JWT认证和密码哈希模块
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from config import config
from jose import JWTError, jwt
from passlib.context import CryptContext

# 密码哈希上下文（使用bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict) -> str:
    """
    创建JWT访问令牌

    Args:
        data: 要编码到token中的数据（通常包含user_id和username）

    Returns:
        JWT token字符串
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    """
    解码JWT token

    Args:
        token: JWT token字符串

    Returns:
        解码后的payload，如果token无效则返回None
    """
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
