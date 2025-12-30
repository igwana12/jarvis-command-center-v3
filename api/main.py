"""
Vercel serverless function entry point for Jarvis Command Center
"""
import sys
import os
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import the FastAPI app from backend
from optimized_main_v2 import app

# Export handler for Vercel
handler = app