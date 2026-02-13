from __future__ import annotations

from typing import TYPE_CHECKING
from app.database.mongodb import get_mongo_db

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase


def get_db() -> "AgnosticDatabase":
    """
    FastAPI dependency: returns the connected Mongo database.
    connect_to_mongo() runs in lifespan, so db should be available.
    """
    db = get_mongo_db()
    if db is None:
        raise RuntimeError("MongoDB is not connected. connect_to_mongo() may not have run yet.")
    return db
