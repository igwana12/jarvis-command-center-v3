"""
Vercel serverless function entry point for Jarvis Command Center
"""
import sys
import os
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import FastAPI and necessary modules
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Create a new FastAPI app instance for Vercel
app = FastAPI(title="Jarvis Command Center API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers from backend modules
try:
    from resource_api import router as resource_router
    from execution_endpoints import router as execution_router

    # Mount routers
    app.include_router(resource_router)
    app.include_router(execution_router)
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    # Create fallback endpoints
    @app.get("/api/resources/all")
    async def get_all_resources():
        return {
            "resources": {
                "skills": [],
                "agents": [],
                "workflows": [],
                "models": [],
                "scripts": []
            },
            "counts": {
                "skills": 0,
                "agents": 0,
                "workflows": 0,
                "models": 0,
                "scripts": 0,
                "total": 0
            }
        }

# Create health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Jarvis Command Center"}

# Export handler for Vercel using Mangum adapter
handler = Mangum(app, lifespan="off")