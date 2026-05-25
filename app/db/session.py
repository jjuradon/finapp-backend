from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass


# Core async engine for modular monolith
engine = create_async_engine(settings.database_url, echo=False)

# Session factory for route handlers and services
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
