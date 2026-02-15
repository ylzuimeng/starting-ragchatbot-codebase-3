import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from config import config
from rag_system import RAGSystem

# Import FastAPI Users components
from auth_config import (
    get_user_manager,
    get_async_session,
    get_jwt_strategy,
    async_session_maker
)
from users import UserTable
from sqlalchemy import select, or_

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)

# ============================================================================
# Pydantic models for request/response
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[str]
    session_id: str

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]

class UserRegister(BaseModel):
    """User registration request"""
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    """User login request"""
    username: str
    password: str

class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    """User information response"""
    id: int
    username: str
    email: str
    is_verified: bool
    is_superuser: bool

# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    """
    User registration endpoint.

    Creates a new user with username and password.
    """
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Create async session
    async with async_session_maker() as session:
        # Check if username exists
        result = await session.execute(
            select(UserTable).where(UserTable.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        # Check if email exists
        result = await session.execute(
            select(UserTable).where(UserTable.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Email already exists"
            )

        # Create new user
        hashed_password = pwd_context.hash(user_data.password)
        new_user = UserTable(
            email=user_data.email,
            hashed_password=hashed_password,
            username=user_data.username,
            is_active=True,
            is_verified=True,
            is_superuser=False
        )

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        # Generate JWT token
        jwt_strategy = get_jwt_strategy()
        token = await jwt_strategy.write_token(new_user)

        return AuthResponse(
            access_token=token,
            user={
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "is_verified": new_user.is_verified,
                "is_superuser": new_user.is_superuser
            }
        )


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(login_data: UserLogin):
    """
    User login endpoint that accepts username or email.

    Supports both username and password authentication.
    """
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with async_session_maker() as session:
        # Find user by username or email
        result = await session.execute(
            select(UserTable).where(
                or_(
                    UserTable.username == login_data.username,
                    UserTable.email == login_data.username
                )
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not pwd_context.verify(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last_login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        await session.commit()

        # Generate JWT token
        jwt_strategy = get_jwt_strategy()
        token = await jwt_strategy.write_token(user)

        return AuthResponse(
            access_token=token,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_verified": user.is_verified,
                "is_superuser": user.is_superuser
            }
        )


async def get_current_user(token: str) -> UserTable:
    """Dependency to get current authenticated user from JWT token."""
    from jose import jwt, JWTError

    try:
        # Verify token and get user ID using the secret key
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Skip audience verification for simplicity
        )
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        # Get user from database
        async with async_session_maker() as session:
            user = await session.get(UserTable, int(user_id))
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="User not found"
                )
            return user

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication credentials: {str(e)}"
        )


# Custom dependency to extract Bearer token
from fastapi import Header

async def get_bearer_token(
    authorization: Optional[str] = Header(None)
) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(
    token: str = Depends(get_bearer_token)
):
    """Get current user information"""
    user = await get_current_user(token)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser
    )


@app.post("/api/auth/logout")
async def logout():
    """User logout (client should delete token)"""
    return {"message": "Successfully logged out"}

# ============================================================================
# Protected API Endpoints
# ============================================================================

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    token: str = Depends(get_bearer_token)
):
    """Process a query and return response with sources"""
    try:
        user = await get_current_user(token)

        session_id = request.session_id
        if not session_id:
            # Create new session for user
            import time
            session_id = f"user_{user.id}_{int(time.time())}"

        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)

        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats(
    token: str = Depends(get_bearer_token)
):
    """Get course analytics and statistics"""
    try:
        # Verify authentication
        await get_current_user(token)

        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=False)
            print(f"Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")


# ============================================================================
# Static Files
# ============================================================================

# Custom static file handler with no-cache headers for development
class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if hasattr(response, 'headers'):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Serve static files for the frontend
app.mount("/", DevStaticFiles(directory="../frontend", html=True), name="static")
