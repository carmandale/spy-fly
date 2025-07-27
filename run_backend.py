#!/usr/bin/env python3
"""
Backend entry point that reads port from environment
This script is called as 'python ../run_backend.py' from the backend directory by start.sh
"""
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env (we're being run from backend directory)
load_dotenv(".env")

# Get port from environment, default to 8003
port = int(os.getenv("API_PORT", 8003))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload for now to fix module import issue
    )