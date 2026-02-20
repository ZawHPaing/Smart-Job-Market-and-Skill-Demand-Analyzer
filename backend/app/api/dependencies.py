from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator
from app.database.mongodb import get_mongo_db
from app.database.neo4j import get_neo4j_driver as _get_neo4j_driver

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase
    from neo4j import AsyncDriver


def get_db() -> "AgnosticDatabase":
    """
    FastAPI dependency: returns the connected Mongo database.
    connect_to_mongo() runs in lifespan, so db should be available.
    """
    db = get_mongo_db()
    if db is None:
        raise RuntimeError("MongoDB is not connected. connect_to_mongo() may not have run yet.")
    return db


async def get_neo4j_driver() -> "AsyncDriver":
    """
    FastAPI dependency: returns the Neo4j driver instance.
    The driver is managed by the app lifespan.
    """
    driver = _get_neo4j_driver()
    if driver is None:
        raise RuntimeError("Neo4j driver is not initialized. It may not have been set up in the app lifespan.")
    return driver