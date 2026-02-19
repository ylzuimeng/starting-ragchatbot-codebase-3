"""
FastAPI Users authentication configuration.

This module sets up JWT authentication using FastAPI Users library,
integrating with our existing user model and database.
"""

from typing import AsyncGenerator, Optional

from config import config
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from users import Base, User, UserCreate, UserTable, UserUpdate

# Async database engine and session
async_engine = create_async_engine("sqlite+aiosqlite:///./users.db", echo=False)

async_session_maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """Get user database instance."""
    yield SQLAlchemyUserDatabase(session, UserTable)


# Custom UserManager to handle last_login updates and username-based login
class UserManager(BaseUserManager[User, int]):
    """Custom user manager with last_login tracking."""

    async def authenticate(
        self, credentials: dict, request: Optional[Request] = None
    ) -> Optional[User]:
        """
        Authenticate user with username or email.

        Supports both username and password authentication for backward compatibility.
        """
        username_or_email = credentials.get("username") or credentials.get("email")
        password = credentials.get("password")

        if not username_or_email or not password:
            return None

        # Find user by username or email
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserTable).where(
                    or_(
                        UserTable.username == username_or_email,
                        UserTable.email == username_or_email,
                    )
                )
            )
            user_obj = result.scalar_one_or_none()

            if user_obj is None:
                return None

            # Verify password
            verified, _ = self.password_helper.verify_and_update(password, user_obj.hashed_password)

            if not verified:
                return None

            # Return user model
            return User.model_validate(user_obj)

    async def on_after_login(self, user: User, request: Optional[Request] = None):
        """Update last_login timestamp after successful login."""
        # Update last_login in database
        async with async_session_maker() as session:
            user_obj = await session.get(UserTable, user.id)
            if user_obj:
                user_obj.last_login = self._now()
                await session.commit()
        print(f"User {user.username} logged in at {self._now()}")

    def _now(self):
        """Get current datetime."""
        from datetime import datetime

        return datetime.utcnow()


# Initialize UserManager
async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """Get user manager instance."""
    yield UserManager(user_db)


# Bearer transport for token authentication
bearer_transport = BearerTransport(tokenUrl="api/auth/jwt/login")


# JWT Strategy
def get_jwt_strategy() -> JWTStrategy:
    """Get JWT authentication strategy."""
    return JWTStrategy(
        secret=config.SECRET_KEY,
        lifetime_seconds=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
    )


# FastAPI Users authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Initialize FastAPIUsers
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)


# Current user dependency
async def current_user(user: User = Depends(fastapi_users.current_user())) -> User:
    """Get current authenticated user."""
    return user


async def current_active_user(
    user: User = Depends(fastapi_users.current_user(active=True)),
) -> User:
    """Get current active user."""
    return user


# Export JWT strategy for use in custom login endpoint
jwt_authentication = get_jwt_strategy()
