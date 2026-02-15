"""
FastAPI Users user models and database configuration.

This module defines the user model with custom fields (username, last_login)
and integrates with FastAPI Users authentication system.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base

from config import config


# SQLAlchemy Base
Base = declarative_base()


class UserTable(Base, AsyncAttrs):
    """
    User table model for SQLAlchemy.

    This model represents the users table in the database.
    It includes both FastAPI Users required fields and custom fields.
    """
    __tablename__ = "users"

    # FastAPI Users required fields
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Custom fields
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# FastAPI Users Pydantic models - simplified for our use case
class User(BaseModel):
    """FastAPI Users base user model for API responses."""
    id: int
    email: str
    username: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = True

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model with username field."""
    email: str
    password: str
    username: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = True


class UserUpdate(BaseModel):
    """User update model."""
    password: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None


# Note: We don't need to create tables here because they already exist
# The migration script has already created the users table with the correct schema
