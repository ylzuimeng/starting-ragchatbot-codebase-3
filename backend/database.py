"""
数据库连接和表管理模块
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator


class Database:
    """数据库管理类"""

    def __init__(self, database_url: str):
        """
        初始化数据库连接

        Args:
            database_url: 数据库连接字符串，例如 sqlite:///./users.db
        """
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator:
        """
        获取数据库会话的上下文管理器

        使用方式:
            with db.get_session() as session:
                session.execute(...)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def init_tables(self):
        """初始化所有数据库表（如果不存在）"""
        with self.engine.begin() as conn:
            # 创建用户表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """))

            # 创建会话历史表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_id VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))

            # 创建用户会话表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_id VARCHAR(100) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))

            # 创建索引
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_username ON users(username)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email ON users(email)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_session ON conversation_history(user_id, session_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_session_id ON user_sessions(session_id)"))
