"""
用户管理模块
"""
from typing import Optional, Dict
from sqlalchemy import text
from database import Database
from models_db import UserCreate, UserLogin, AuthResponse, UserResponse
from auth import verify_password, get_password_hash, create_access_token


class UserManager:
    """用户管理器"""

    def __init__(self, db: Database):
        """
        初始化用户管理器

        Args:
            db: 数据库实例
        """
        self.db = db

    def create_user(self, user_data: UserCreate) -> AuthResponse:
        """
        创建新用户

        Args:
            user_data: 用户注册信息

        Returns:
            包含access_token和user信息的认证响应

        Raises:
            ValueError: 如果用户名已存在
        """
        with self.db.get_session() as session:
            # 检查用户名是否已存在
            result = session.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {"username": user_data.username}
            ).fetchone()

            if result:
                raise ValueError("Username already exists")

            # 检查邮箱是否已存在
            result = session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": user_data.email}
            ).fetchone()

            if result:
                raise ValueError("Email already exists")

            # 创建用户
            password_hash = get_password_hash(user_data.password)
            result = session.execute(
                text("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (:username, :email, :password_hash)
                    RETURNING id, username, email, created_at
                """),
                {
                    "username": user_data.username,
                    "email": user_data.email,
                    "password_hash": password_hash
                }
            ).fetchone()

            # 生成token
            token_data = {"user_id": result[0], "username": result[1]}
            access_token = create_access_token(token_data)

            return AuthResponse(
                access_token=access_token,
                user=UserResponse(
                    id=result[0],
                    username=result[1],
                    email=result[2],
                    created_at=str(result[3]) if result[3] else None
                )
            )

    def authenticate_user(self, login_data: UserLogin) -> AuthResponse:
        """
        验证用户并返回token

        Args:
            login_data: 用户登录信息

        Returns:
            包含access_token和user信息的认证响应

        Raises:
            ValueError: 如果用户名或密码错误
        """
        with self.db.get_session() as session:
            result = session.execute(
                text("""
                    SELECT id, username, email, password_hash
                    FROM users WHERE username = :username
                """),
                {"username": login_data.username}
            ).fetchone()

            if not result or not verify_password(login_data.password, result[3]):
                raise ValueError("Invalid username or password")

            # 更新最后登录时间
            session.execute(
                text("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = :id"),
                {"id": result[0]}
            )

            # 生成token
            token_data = {"user_id": result[0], "username": result[1]}
            access_token = create_access_token(token_data)

            return AuthResponse(
                access_token=access_token,
                user=UserResponse(
                    id=result[0],
                    username=result[1],
                    email=result[2]
                )
            )

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        通过ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            用户信息字典，如果不存在则返回None
        """
        with self.db.get_session() as session:
            result = session.execute(
                text("""
                    SELECT id, username, email, created_at
                    FROM users WHERE id = :user_id
                """),
                {"user_id": user_id}
            ).fetchone()

            if not result:
                return None

            return {
                "id": result[0],
                "username": result[1],
                "email": result[2],
                "created_at": str(result[3]) if result[3] else None
            }
