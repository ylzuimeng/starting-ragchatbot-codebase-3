"""
Shared pytest fixtures and test utilities for RAG system tests.

This module provides common fixtures for mocking components, test data setup,
and test configuration across all test modules.
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typing import Generator, Optional
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


# ============================================================================
# Test Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config() -> Config:
    """
    Provides a test configuration with safe defaults.

    All file paths use temporary directories to avoid polluting the project.
    API keys are mocked to avoid real API calls.
    """
    config = Config()
    config.CHROMA_PATH = tempfile.mkdtemp(prefix="test_chroma_")
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.ZHIPUAI_API_KEY = "test_zhipuai_key"
    config.ANTHROPIC_API_KEY = "test_anthropic_key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.ANTHROPIC_BASE_URL = None
    config.SECRET_KEY = "test-secret-key-for-jwt"
    config.DATABASE_URL = "sqlite:///./test_users.db"
    return config


@pytest.fixture
def test_temp_dir() -> Generator[Path, None, None]:
    """
    Provides a temporary directory that is automatically cleaned up after tests.

    Useful for creating test files, documents, or database files.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="test_rag_"))
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# ============================================================================
# Mock Component Fixtures
# ============================================================================

@pytest.fixture
def mock_vector_store():
    """Provides a mocked VectorStore for testing."""
    from vector_store import VectorStore, SearchResults

    mock_store = Mock(spec=VectorStore)

    # Setup default search results
    mock_results = SearchResults(
        documents=["Test content chunk"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.1],
        error=None
    )
    mock_store.search.return_value = mock_results
    mock_store.get_lesson_link.return_value = "http://example.com/lesson/1"
    mock_store.get_course_link.return_value = "http://example.com/course"

    return mock_store


@pytest.fixture
def mock_ai_generator():
    """Provides a mocked AIGenerator for testing."""
    from ai_generator import AIGenerator

    mock_ai = Mock(spec=AIGenerator)
    mock_ai.generate_response.return_value = "Test AI response"

    return mock_ai


@pytest.fixture
def mock_session_manager():
    """Provides a mocked SessionManager for testing."""
    mock_mgr = Mock()
    mock_mgr.get_conversation_history.return_value = None
    mock_mgr.add_exchange.return_value = None
    return mock_mgr


@pytest.fixture
def mock_document_processor():
    """Provides a mocked DocumentProcessor for testing."""
    from document_processor import DocumentProcessor

    mock_proc = Mock(spec=DocumentProcessor)
    mock_proc.process_document.return_value = (
        ["Test Course"],  # course_metadata
        ["Test content chunk"]  # chunks
    )

    return mock_proc


@pytest.fixture
def mock_tool_manager():
    """Provides a mocked ToolManager for testing."""
    from search_tools import ToolManager

    mock_mgr = Mock(spec=ToolManager)
    mock_mgr.get_tool_definitions.return_value = [
        {"name": "search_course_content", "description": "Search course materials"},
        {"name": "get_course_outline", "description": "Get course outline"}
    ]
    mock_mgr.get_last_sources.return_value = [
        {"text": "Test Course - Lesson 1", "link": "http://example.com/lesson/1"}
    ]
    mock_mgr.execute_tool.return_value = "Tool result"
    mock_mgr.reset_sources.return_value = None

    return mock_mgr


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_course_document() -> str:
    """
    Provides a sample course document in the expected format.

    Returns document text that follows the structure expected by
    DocumentProcessor.
    """
    return """Course Title: Complete Python Programming
Course Link: https://example.com/python-course
Course Instructor: Jane Doe
Lesson 0: Introduction to Python
Lesson Link: https://example.com/python-course/intro
Python is a high-level, interpreted programming language known for its simplicity and readability.
It was created by Guido van Rossum and first released in 1991.

Lesson 1: Variables and Data Types
Lesson Link: https://example.com/python-course/variables
In Python, variables are created when you assign a value to them. Python supports various data types including integers, floats, strings, booleans, lists, tuples, dictionaries, and sets.

Lesson 2: Control Flow
Lesson Link: https://example.com/python-course/control-flow
Python supports if statements, for loops, while loops, and other control flow structures similar to other programming languages.
"""


@pytest.fixture
def sample_search_results():
    """
    Provides sample search results for testing.

    Returns SearchResults object with typical data structure.
    """
    from vector_store import SearchResults

    return SearchResults(
        documents=[
            "Python variables are used to store data values.",
            "Python has several built-in data types including int, float, str, and bool.",
            "Lists in Python are ordered, mutable collections."
        ],
        metadata=[
            {"course_title": "Complete Python Programming", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Complete Python Programming", "lesson_number": 1, "chunk_index": 1},
            {"course_title": "Complete Python Programming", "lesson_number": 2, "chunk_index": 0}
        ],
        distances=[0.12, 0.15, 0.22],
        error=None
    )


@pytest.fixture
def sample_course_metadata():
    """
    Provides sample course metadata for testing.

    Returns dictionary with course information.
    """
    import json

    lessons = [
        {"lesson_number": 0, "lesson_title": "Introduction to Python", "lesson_link": "https://example.com/intro"},
        {"lesson_number": 1, "lesson_title": "Variables and Data Types", "lesson_link": "https://example.com/variables"},
        {"lesson_number": 2, "lesson_title": "Control Flow", "lesson_link": "https://example.com/control-flow"}
    ]

    return {
        "title": "Complete Python Programming",
        "course_link": "https://example.com/python-course",
        "instructor": "Jane Doe",
        "lessons_json": json.dumps(lessons)
    }


# ============================================================================
# Test User Authentication Fixtures
# ============================================================================

@pytest.fixture
def test_user_data():
    """
    Provides sample user registration/login data for testing auth endpoints.
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }


@pytest.fixture
def test_auth_headers():
    """
    Provides sample authentication headers for testing protected endpoints.

    Contains a mock Bearer token.
    """
    return {"Authorization": "Bearer mock_jwt_token_for_testing"}


@pytest.fixture
def mock_jwt_token():
    """
    Provides a mock JWT token for testing.

    This is a valid-looking JWT token structure (not actually valid).
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.payload.signature"


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
async def test_db_session():
    """
    Provides an async database session for testing.

    Uses an in-memory SQLite database for isolated test execution.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from users import Base

    # Use in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with async_session_maker() as session:
        yield session


# ============================================================================
# HTTP Test Client Fixtures
# ============================================================================

@pytest.fixture
def mock_rag_system():
    """
    Provides a mocked RAGSystem for testing API endpoints.

    The RAGSystem is the main orchestrator, so this fixture allows
    testing the API layer without real RAG operations.
    """
    from rag_system import RAGSystem

    mock_rag = Mock(spec=RAGSystem)
    mock_rag.query.return_value = (
        "Test answer to the query",
        [{"text": "Test Course - Lesson 1", "link": "http://example.com/lesson/1"}]
    )
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 1,
        "course_titles": ["Test Course"]
    }

    return mock_rag


# ============================================================================
# Anthropic Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_response():
    """
    Provides a mock Anthropic API response for testing.

    Includes the TextBlock structure used by the anthropic library.
    """
    class MockTextBlock:
        def __init__(self, type: str, text: str):
            self.type = type
            self.text = text

    class MockToolUseBlock:
        def __init__(self, id: str, name: str, input: dict, type: str):
            self.id = id
            self.name = name
            self.input = input
            self.type = type

    class MockResponse:
        def __init__(self, stop_reason: str, content):
            self.stop_reason = stop_reason
            self.content = content

    return {
        "TextBlock": MockTextBlock,
        "ToolUseBlock": MockToolUseBlock,
        "Response": MockResponse
    }


# ============================================================================
# Cleanup and Setup Hooks
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_databases(test_temp_dir):
    """
    Auto-cleanup fixture that runs after each test.

    Removes test databases and temporary files created during tests.
    """
    yield
    # Cleanup happens after test completes
    pass
