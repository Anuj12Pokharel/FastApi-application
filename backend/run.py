"""
Start script for the RAG application backend with proper uvicorn configuration.
This script ensures that the virtual environment is excluded from file watching.
"""
import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
    
    # Configure uvicorn to exclude .venv and other directories from reload watching
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./"],  # Only watch current directory
        reload_excludes=[
            ".venv/*",
            ".venv/**/*",
            "__pycache__/*",
            "*.pyc",
            "chroma_db/*",
            "chroma_db_local/*",
            "*.log",
            "*.txt"
        ],
        log_level="info"
    )
