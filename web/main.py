"""
FastAPI web application for DJ MP3 Renamer.

Provides REST API endpoints and serves static frontend files.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DJ MP3 Renamer",
    description="Batch rename MP3 files with metadata-based templates",
    version="1.0.0"
)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "api": "ready"
    }


# Root endpoint - serve main HTML page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application page."""
    index_path = static_dir / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")

    return FileResponse(index_path)


# CORS middleware (if needed for development)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
