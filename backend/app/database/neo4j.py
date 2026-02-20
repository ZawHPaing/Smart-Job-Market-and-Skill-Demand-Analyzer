from neo4j import AsyncGraphDatabase
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jConnection:
    _instance = None

    @classmethod
    async def get_driver(cls):
        if cls._instance is None:
            uri = os.getenv("NEO4J_URI")
            user = os.getenv("NEO4J_USER")
            password = os.getenv("NEO4J_PASSWORD")

            print(f"🔌 Connecting to Neo4j at {uri} as {user}")

            cls._instance = AsyncGraphDatabase.driver(
                uri,
                auth=(user, password)
            )

            # Better connectivity check
            await cls._instance.verify_connectivity()

            print("✅ Neo4j connection successful")

        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


async def get_neo4j_driver():
    return await Neo4jConnection.get_driver()