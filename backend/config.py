import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "")  # Optional: Custom base URL for Anthropic-compatible APIs

    # ZhipuAI embedding settings
    ZHIPUAI_API_KEY: str = os.getenv("ZHIPUAI_API_KEY", "")
    ZHIPUAI_MODEL: str = "embedding-3"

    # JWT Authentication settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./users.db")

    # Document processing settings
    CHUNK_SIZE: int = 800       # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100     # Characters to overlap between chunks
    MAX_RESULTS: int = 5         # Maximum search results to return
    MAX_HISTORY: int = 2         # Number of conversation messages to remember

    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

    # Tool calling settings
    MAX_TOOL_ROUNDS: int = 2  # Maximum sequential tool calling rounds per query

config = Config()


