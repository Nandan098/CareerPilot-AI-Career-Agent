"""Database engine, SQLAlchemy base, and request-scoped sessions."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class inherited by every database model."""


def get_db():
    """Yield one database session per API request, then always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
