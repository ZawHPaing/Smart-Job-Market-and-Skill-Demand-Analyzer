from neo4j import AsyncGraphDatabase
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jConnection:
    _instance: Optional[AsyncGraphDatabase.driver] = None
    
    @classmethod
    async def get_driver(cls):
        if cls._instance is None:
            # ⚠️ UPDATE THESE TO MATCH YOUR NEO4J INSTALLATION
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")  # or "bolt://127.0.0.1:7687"
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "12345678")  # Your actual Neo4j password
            
            print(f"🔌 Connecting to Neo4j at {uri} as {user}")
            
            try:
                cls._instance = AsyncGraphDatabase.driver(
                    uri, 
                    auth=(user, password)
                )
                # Test connection
                async with cls._instance.session() as session:
                    await session.run("RETURN 1")
                print("✅ Neo4j connection successful")
            except Exception as e:
                print(f"❌ Neo4j connection failed: {e}")
                raise
                
        return cls._instance
    
    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

async def get_neo4j_driver():
    """Dependency for FastAPI to get Neo4j driver"""
    driver = await Neo4jConnection.get_driver()
    return driver