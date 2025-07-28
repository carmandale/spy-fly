"""Database session management utilities."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db_session() as session:
            # Use session here
            session.query(Model).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_async_db():
    """
    Dependency for FastAPI routes to get database session.

    This function is already defined in database.py as get_db()
    This is just a placeholder for async support in the future.
    """
    pass
