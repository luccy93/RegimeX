"""
RegimeX Database Foundation
===========================
Exports core database infrastructure components: DeclarativeBase,
engine management, session factories, and dependency hooks.
"""

from app.core.database.base import Base
from app.core.database.session import (
    create_engine_and_session_factory,
    dispose_engine,
    get_db_session,
    get_engine,
    get_session_factory,
    transaction_context,
)

__all__ = [
    "Base",
    "create_engine_and_session_factory",
    "dispose_engine",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "transaction_context",
]
