import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGODB_DB_NAME", "myappdb")

# Global connection objects
mongo_client = None
database = None

async def connect_to_mongo():
    global mongo_client, database
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URL)
        database = mongo_client[MONGO_DB_NAME]
        # Test connection
        await database.command("ping")
        print(f"✓ Connected to MongoDB at {MONGO_URL}")
        return True
    except Exception as e:
        print(f"✗ Error connecting to MongoDB: {e}")
        return False

async def close_mongo_connection():
    global mongo_client
    if mongo_client:
        mongo_client.close()
        print("MongoDB connection closed")

def get_mongo_db():
    return database