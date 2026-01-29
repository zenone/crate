"""
FastAPI web application for DJ MP3 Renamer.

Provides REST API endpoints and serves static frontend files.
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
import logging

# Import the RenamerAPI
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class DirectoryRequest(BaseModel):
    path: str


class FileInfo(BaseModel):
    path: str
    name: str
    size: int
    is_mp3: bool
    metadata: Optional[dict] = None


class DirectoryContents(BaseModel):
    path: str
    files: List[FileInfo]
    total_files: int
    mp3_count: int


class TemplateRequest(BaseModel):
    template: str


class PreviewRequest(BaseModel):
    path: str
    recursive: bool = False
    template: Optional[str] = None


class ConfigUpdate(BaseModel):
    updates: dict


class DirectoryBrowseRequest(BaseModel):
    path: Optional[str] = None  # None = start at home
    include_parent: bool = True


class DirectoryInfo(BaseModel):
    name: str
    path: str


class DirectoryBrowseResponse(BaseModel):
    current_path: str
    parent_path: Optional[str]
    directories: List[DirectoryInfo]
    path_parts: List[str]


# Create FastAPI app
app = FastAPI(
    title="DJ MP3 Renamer",
    description="Batch rename MP3 files with metadata-based templates",
    version="1.0.0"
)

# Initialize RenamerAPI (shared instance)
renamer_api = RenamerAPI(workers=2)
logger.info("RenamerAPI initialized with 2 workers")

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


# Directory browser endpoint (for modal navigation)
@app.post("/api/directory/browse", response_model=DirectoryBrowseResponse)
async def browse_directory(request: DirectoryBrowseRequest):
    """Browse filesystem for directory selection (shows folders only)."""
    try:
        # Default to home directory if no path provided
        if request.path is None or request.path == '':
            dir_path = Path.home()
        else:
            dir_path = Path(request.path).expanduser().resolve()

        if not dir_path.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")

        if not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")

        # Get parent directory
        parent_path = str(dir_path.parent) if dir_path.parent != dir_path else None

        # List subdirectories only (not files)
        directories = []
        try:
            for item in sorted(dir_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    directories.append(DirectoryInfo(
                        name=item.name,
                        path=str(item)
                    ))
        except PermissionError:
            # If we can't read the directory, return empty list
            pass

        # Build path parts for breadcrumb
        path_parts = list(dir_path.parts)

        return DirectoryBrowseResponse(
            current_path=str(dir_path),
            parent_path=parent_path,
            directories=directories,
            path_parts=path_parts
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Directory browsing endpoint
@app.post("/api/directory/list", response_model=DirectoryContents)
async def list_directory(request: DirectoryRequest):
    """List files in a directory with MP3 metadata."""
    try:
        dir_path = Path(request.path).expanduser().resolve()

        if not dir_path.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")

        if not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")

        # List all files
        files = []
        mp3_count = 0

        for file_path in sorted(dir_path.iterdir()):
            if file_path.is_file():
                is_mp3 = file_path.suffix.lower() == '.mp3'

                file_info = FileInfo(
                    path=str(file_path),
                    name=file_path.name,
                    size=file_path.stat().st_size,
                    is_mp3=is_mp3,
                    metadata=None  # Will load on demand
                )

                files.append(file_info)
                if is_mp3:
                    mp3_count += 1

        return DirectoryContents(
            path=str(dir_path),
            files=files,
            total_files=len(files),
            mp3_count=mp3_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing directory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# File metadata endpoint
@app.post("/api/file/metadata")
async def get_file_metadata(request: DirectoryRequest):
    """Get metadata for a specific MP3 file."""
    try:
        file_path = Path(request.path).expanduser().resolve()

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.path}")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {request.path}")

        # Use the API to analyze the file
        metadata = renamer_api.analyze_file(file_path)

        if metadata is None:
            raise HTTPException(status_code=400, detail="Could not read file metadata")

        return {
            "path": str(file_path),
            "name": file_path.name,
            "metadata": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Template validation endpoint
@app.post("/api/template/validate")
async def validate_template(request: TemplateRequest):
    """Validate a filename template."""
    try:
        result = renamer_api.validate_template(request.template)
        return result.to_dict()

    except Exception as e:
        logger.error(f"Error validating template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Preview rename endpoint
@app.post("/api/rename/preview")
async def preview_rename(request: PreviewRequest):
    """Preview rename operation without executing."""
    try:
        path = Path(request.path).expanduser().resolve()

        rename_request = RenameRequest(
            path=path,
            recursive=request.recursive,
            dry_run=True,  # Always dry run for preview
            template=request.template,
            auto_detect=True
        )

        previews = renamer_api.preview_rename(rename_request)

        # Convert to JSON-serializable format
        preview_list = [preview.to_dict() for preview in previews]

        return {
            "path": str(path),
            "previews": preview_list,
            "total": len(preview_list)
        }

    except Exception as e:
        logger.error(f"Error generating preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Configuration endpoints
@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    try:
        config = renamer_api.get_config()
        return config
    except Exception as e:
        logger.error(f"Error getting config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/update")
async def update_config(request: ConfigUpdate):
    """Update configuration."""
    try:
        success = renamer_api.update_config(request.updates)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update configuration")

        return {"success": True, "message": "Configuration updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
