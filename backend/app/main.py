from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.database.neo4j_db import connect_to_neo4j, close_neo4j_connection
from app.api.endpoints import router as api_router
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await connect_to_neo4j()
    print("Backend started successfully!")
    yield
    # Shutdown
    await close_mongo_connection()
    await close_neo4j_connection()

app = FastAPI(title="FullStack API", version="1.0.0", lifespan=lifespan)

# CORS configuration for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI + MongoDB + Neo4j API"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "fullstack-api",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)