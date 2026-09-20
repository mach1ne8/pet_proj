"""Backward-compatible imports for the database layer."""

from core.config import DATABASE_URL
from core.database import Base, SessionLocal, engine, get_db

__all__ = [
    "DATABASE_URL",
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
]
