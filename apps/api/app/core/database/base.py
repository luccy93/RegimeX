"""
RegimeX Database Foundation — Declarative Base
==============================================
Defines the modern SQLAlchemy 2.x DeclarativeBase superclass with
standardized naming conventions for database constraints and indexes.

Constraint naming convention:
- ix: Index
- uq: Unique constraint
- ck: Check constraint
- fk: Foreign key constraint
- pk: Primary key constraint
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Standard metadata naming conventions ensure deterministic names across
# PostgreSQL, SQLite, and Alembic auto-migrations.
POSTGRES_NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all RegimeX SQLAlchemy ORM models."""

    metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)
