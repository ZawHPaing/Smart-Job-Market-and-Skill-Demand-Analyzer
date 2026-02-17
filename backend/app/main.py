# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.endpoints import router as api_router
import uvicorn
import asyncio
import subprocess
import sys
import os

async def warmup_cache():
    """Run warmup script in background without blocking startup"""
    try:
        # Wait a bit for the server to fully start
        await asyncio.sleep(2)
        
        # Get the path to the warmup script
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "warmup.py")
        
        # Run warmup in a subprocess so it doesn't block
        subprocess.Popen([sys.executable, script_path])
        print("🔥 Cache warmup started in background")
    except Exception as e:
        print(f"⚠️ Failed to start cache warmup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    print("✅ Backend started successfully!")
    
    # Start cache warmup in background
    asyncio.create_task(warmup_cache())
    
    yield
    # Shutdown
    await close_mongo_connection()
    print("👋 Backend shut down")

app = FastAPI(
    title="FullStack API", 
    version="1.0.0", 
    lifespan=lifespan
)

# ===== SINGLE CORS MIDDLEWARE - MUST BE FIRST =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include API router
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "FullStack API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "fullstack-api"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)