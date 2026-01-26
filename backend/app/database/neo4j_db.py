import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = None

async def connect_to_neo4j():
    global driver
    try:
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            encrypted=False  # Set to True for Neo4j Aura
        )
        await driver.verify_connectivity()
        print(f"✓ Connected to Neo4j at {NEO4J_URI}")
        return True
    except Exception as e:
        print(f"✗ Error connecting to Neo4j: {e}")
        return False

async def close_neo4j_connection():
    global driver
    if driver:
        await driver.close()
        print("Neo4j connection closed")

def get_neo4j_driver():
    return driver

async def execute_cypher_query(query, parameters=None):
    driver = get_neo4j_driver()
    if not driver:
        raise Exception("Neo4j driver not initialized")
    
    async with driver.session() as session:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records