import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from src.common.config.settings import get_settings
from src.common.errors.exceptions import DatabaseConnectionError

logger = logging.getLogger("eakap.database.connection")

# Retrieve validation settings
settings = get_settings()

# For local development with SQLite, ensure that the path to the DB file and directories exist
if settings.DATABASE_URL.startswith("sqlite:///"):
    # Strip URL prefix and resolve path
    db_file_relative_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_file_path = Path(db_file_relative_path).resolve()
    db_file_path.parent.mkdir(parents=True, exist_ok=True)

try:
    # check_same_thread=False allows multi-threaded requests in SQLite (e.g. tests or Streamlit requests)
    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True  # Proactively pings connection to drop stale links
    )
    
    # Session factory config
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
except Exception as e:
    raise DatabaseConnectionError(
        message="Critical Failure: Could not establish SQLAlchemy database engine client.",
        original_exception=e
    )

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager that yields an active SQLAlchemy transactional session.
    Automatically commits transactions on success, rolls back on error, and closes connections.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Transaction failed, session rollback triggered: {str(e)}")
        raise e
    finally:
        session.close()

def verify_connection() -> bool:
    """
    Verifies database connectivity by executing a basic diagnostic query.
    Returns True if healthy, raises DatabaseConnectionError on failure.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        raise DatabaseConnectionError(
            message="Database connectivity check failed. Relational store is unreachable.",
            original_exception=e
        )
