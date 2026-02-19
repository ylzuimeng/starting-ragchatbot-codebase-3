"""
数据库模型和Pydantic schemas
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr


# 请求模型
class UserCreate(BaseModel):
    """用户注册请求"""

    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """用户登录请求"""

    username: str
    password: str


# 响应模型
class UserResponse(BaseModel):
    """用户信息响应"""

    id: int
    username: str
    email: str
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    """认证响应"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SessionHistoryResponse(BaseModel):
    """会话历史响应"""

    session_id: str
    created_at: str
    last_accessed: str
    message_count: int
