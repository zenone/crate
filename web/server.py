"""
FastAPI web server for DJ MP3 Renamer.

This server wraps the existing dj_mp3_renamer API and provides
a REST API for the web frontend.
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import the existing API (maintains API-first architecture)
from dj_mp3_renamer.api import RenamerAPI, RenameRequest, RenameStatus
from dj_mp3_renamer.core.template import DEFAULT_TEMPLATE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DJ MP3 Renamer Web API",
    description="Modern web interface for batch MP3 renaming",
    version="1.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
CURRENT_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=CURRENT_DIR / "static"), name="static")

# Upload directory
UPLOAD_DIR = CURRENT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize the renamer API
renamer_api = RenamerAPI(workers=4, logger=logger)


# ======================== Models ========================


class RenameRequestModel(BaseModel):
    """Request model for rename operation."""

    session_id: str
    template: Optional[str] = DEFAULT_TEMPLATE
    dry_run: bool = True
    recursive: bool = False


class RenameResultModel(BaseModel):
    """Result model for rename operation."""

    total: int
    renamed: int
    skipped: int
    errors: int
    results: List[dict]


class TemplateInfo(BaseModel):
    """Available template tokens."""

    default: str
    tokens: dict


# ======================== Routes ========================


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse(CURRENT_DIR / "templates" / "index.html")


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Handle file uploads.

    Files are saved to a temporary session directory.
    Returns session ID for subsequent operations.
    """
    import uuid

    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = []
    for file in files:
        if not file.filename.lower().endswith(".mp3"):
            continue

        file_path = session_dir / file.filename
        with file_path.open("wb") as buffer:
            content = await file.read()
            buffer.write(content)

        uploaded_files.append({"name": file.filename, "size": len(content)})

    logger.info(f"Uploaded {len(uploaded_files)} files to session {session_id}")

    return JSONResponse(
        {
            "session_id": session_id,
            "files": uploaded_files,
            "count": len(uploaded_files),
        }
    )


@app.post("/api/rename", response_model=RenameResultModel)
async def rename_files(request: RenameRequestModel):
    """
    Execute rename operation using the existing API.

    This endpoint wraps dj_mp3_renamer.api.RenamerAPI
    """
    session_dir = UPLOAD_DIR / request.session_id

    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Create RenameRequest for the existing API
    rename_request = RenameRequest(
        path=session_dir,
        recursive=request.recursive,
        dry_run=request.dry_run,
        template=request.template or DEFAULT_TEMPLATE,
    )

    # Use the existing API
    status: RenameStatus = renamer_api.rename_files(rename_request)

    # Convert results to JSON-serializable format
    results = []
    for result in status.results:
        results.append(
            {
                "src": result.src.name,
                "dst": result.dst.name if result.dst else None,
                "status": result.status,
                "message": result.message,
            }
        )

    logger.info(
        f"Rename operation: {status.renamed} renamed, "
        f"{status.skipped} skipped, {status.errors} errors"
    )

    return RenameResultModel(
        total=status.total,
        renamed=status.renamed,
        skipped=status.skipped,
        errors=status.errors,
        results=results,
    )


@app.post("/api/download/{session_id}")
async def download_files(session_id: str):
    """
    Download renamed files as a zip archive.
    """
    import zipfile
    from io import BytesIO

    session_dir = UPLOAD_DIR / session_id

    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Create zip in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for mp3_file in session_dir.glob("*.mp3"):
            zip_file.write(mp3_file, mp3_file.name)

    zip_buffer.seek(0)

    return FileResponse(
        zip_buffer,
        media_type="application/zip",
        filename=f"renamed_mp3s_{session_id[:8]}.zip",
    )


@app.delete("/api/session/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up session directory."""
    session_dir = UPLOAD_DIR / session_id

    if session_dir.exists():
        shutil.rmtree(session_dir)
        logger.info(f"Cleaned up session {session_id}")
        return {"message": "Session cleaned up"}

    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/templates", response_model=TemplateInfo)
async def get_templates():
    """
    Get available template tokens and examples.
    """
    return TemplateInfo(
        default=DEFAULT_TEMPLATE,
        tokens={
            "artist": "Artist name",
            "title": "Title (mix stripped)",
            "mix": "Mix/remix/version",
            "mix_paren": "Mix in parentheses",
            "bpm": "Beats per minute",
            "key": "Musical key",
            "camelot": "Camelot notation",
            "kb": "Key + BPM in brackets",
            "year": "Release year",
            "label": "Record label",
            "album": "Album name",
            "track": "Track number",
        },
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


# Run with: uvicorn web.server:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
