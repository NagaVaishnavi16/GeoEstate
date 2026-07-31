"""SQLAlchemy declarative base used by all persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class that owns application SQLAlchemy metadata."""
