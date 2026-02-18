"""
FastAPI web application for Crate.

Provides REST API endpoints and serves static frontend files.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, cast
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import crate

# Import the RenamerAPI
from crate.api import RenamerAPI, RenameRequest
from crate.api.renamer import OperationCancelled
from crate.core.config import is_first_run, load_config, mark_first_run_complete
from crate.core.context_detection import (
    analyze_context,
    analyze_per_album_context,
    get_default_suggestion,
)
from crate.core.io import find_mp3s
from web.streaming import stream_rename_progress  # Task #124: Streaming progress

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class DirectoryRequest(BaseModel):
    path: str
    recursive: bool = False  # Include subdirectories
    write_metadata: bool = False  # Write BPM/Key to disk (default: read-only)


class FileInfo(BaseModel):
    path: str
    name: str
    size: int
    is_mp3: bool
    metadata: Optional[dict] = None
    modified_time: Optional[float] = None  # Unix timestamp
    created_time: Optional[float] = None  # Unix timestamp


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
    file_paths: Optional[List[str]] = None  # Specific files to preview
    enhance_metadata: bool = False  # Enable MusicBrainz/audio analysis metadata


class ExecuteRenameRequest(BaseModel):
    path: str
    file_paths: List[str]  # Specific files to rename
    template: Optional[str] = None
    dry_run: bool = False


class ConfigUpdate(BaseModel):
    updates: dict


class DirectoryBrowseRequest(BaseModel):
    path: Optional[str] = None  # None = start at home
    include_parent: bool = True
    include_files: bool = False  # Include MP3 files in response


class DirectoryInfo(BaseModel):
    name: str
    path: str


class BrowserFileInfo(BaseModel):
    name: str
    path: str
    size: int


class DirectoryBrowseResponse(BaseModel):
    current_path: str
    parent_path: Optional[str]
    directories: List[DirectoryInfo]
    files: List[BrowserFileInfo]
    path_parts: List[str]


class AnalyzeContextRequest(BaseModel):
    files: List[FileInfo]


class TemplateSuggestionResponse(BaseModel):
    template: str
    reason: str
    preset_id: Optional[str] = None


class ContextAnalysisResponse(BaseModel):
    type: str
    confidence: float
    album_name: Optional[str]
    file_count: int
    track_range: Optional[str]
    suggested_templates: List[TemplateSuggestionResponse]
    warnings: List[str]


class AnalyzeContextResponse(BaseModel):
    contexts: List[ContextAnalysisResponse]
    has_multiple_contexts: bool
    default_suggestion: Optional[dict] = None


# Undo session management
@dataclass
class UndoSession:
    """
    Stores information needed to undo a rename operation.

    Sessions expire after 10 minutes to prevent memory buildup
    and to match user expectations (undo should be immediate).
    """
    session_id: str
    pairs: List[tuple[str, str]]  # [(old_path, new_path), ...]
    created_at: datetime
    expires_at: datetime

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at

    @classmethod
    def create(cls, pairs: List[tuple[str, str]], expires_in_seconds: int = 600):
        """Create a new undo session with expiration time."""
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(seconds=expires_in_seconds)
        return cls(
            session_id=session_id,
            pairs=pairs,
            created_at=created_at,
            expires_at=expires_at
        )


# In-memory session store (use Redis for production)
undo_sessions: dict[str, UndoSession] = {}

# Track which operations have had undo sessions created
undo_sessions_created: set[str] = set()


def cleanup_expired_sessions():
    """Remove expired undo sessions from memory."""
    global undo_sessions
    expired_ids = [
        sid for sid, session in undo_sessions.items()
        if session.is_expired()
    ]
    for sid in expired_ids:
        del undo_sessions[sid]
        logger.info(f"Cleaned up expired undo session: {sid}")


# Create FastAPI app
app = FastAPI(
    title="Crate",
    description="Batch rename MP3 files with metadata-based templates",
    version=crate.__version__,
)

# CORS middleware
# Default: OFF (same-origin only). This avoids exposing state-changing endpoints
# to arbitrary websites (CSRF-style risks).
if os.environ.get("CRATE_ENABLE_CORS") == "1":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
        "version": crate.__version__,
        "api": "ready",
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

        # List subdirectories and optionally files
        directories = []
        files = []
        try:
            # Case-insensitive alphabetical sorting
            items = sorted(dir_path.iterdir(), key=lambda x: x.name.lower())
            for item in items:
                if item.is_dir() and not item.name.startswith('.'):
                    directories.append(DirectoryInfo(
                        name=item.name,
                        path=str(item)
                    ))
                elif request.include_files and item.is_file() and item.suffix.lower() == '.mp3':
                    files.append(BrowserFileInfo(
                        name=item.name,
                        path=str(item),
                        size=item.stat().st_size
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
            files=files,
            path_parts=path_parts
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/directory/initial")
async def get_initial_directory():
    """
    Get initial directory to load on startup with intelligent fallback (Task #84).

    Returns directory to auto-load based on:
    - last_directory config value (if remember_last_directory enabled)
    - Validates path exists, walks up parents if needed
    - Falls back to home directory

    Returns:
        {
            "path": "/Users/dj/Music",
            "source": "remembered|fallback|home",
            "original_path": "/Users/dj/Music/Albums" (if fell back)
        }
    """
    try:
        from crate.core.config import get_valid_directory_with_fallback, load_config

        config = load_config()

        # Check if feature is enabled
        remember_enabled = config.get("remember_last_directory", True)
        saved_path = config.get("last_directory", "")

        if not remember_enabled or not saved_path:
            # Feature disabled or no saved path - return home
            return {
                "path": str(Path.home()),
                "source": "home",
                "original_path": None
            }

        # Get valid directory with fallback
        valid_path = get_valid_directory_with_fallback(saved_path)

        # Determine source
        if valid_path == saved_path:
            source = "remembered"
            original_path = None
        elif valid_path == str(Path.home()):
            source = "home"
            original_path = saved_path
        else:
            source = "fallback"
            original_path = saved_path

        return {
            "path": valid_path,
            "source": source,
            "original_path": original_path
        }

    except Exception as e:
        logger.error(f"Error getting initial directory: {e}", exc_info=True)
        # On any error, return home directory
        return {
            "path": str(Path.home()),
            "source": "home",
            "original_path": None
        }


# Directory browsing endpoint
@app.post("/api/directory/list", response_model=DirectoryContents)
async def list_directory(request: DirectoryRequest):
    """List files in a directory with MP3 metadata (optionally recursive)."""
    try:
        dir_path = Path(request.path).expanduser().resolve()

        if not dir_path.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")

        if not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")

        # Find MP3 files (optionally recursive)
        if request.recursive:
            # Use find_mp3s for recursive scanning
            mp3_files = find_mp3s(dir_path, recursive=True)

            # Create FileInfo objects for MP3s (case-insensitive sort)
            files = []
            for mp3_path in sorted(mp3_files, key=lambda x: x.name.lower()):
                stat_info = mp3_path.stat()
                files.append(FileInfo(
                    path=str(mp3_path),
                    name=mp3_path.name,
                    size=stat_info.st_size,
                    is_mp3=True,
                    metadata=None,  # Will load on demand
                    modified_time=stat_info.st_mtime,
                    created_time=stat_info.st_ctime
                ))

            mp3_count = len(files)
            total_files = len(files)
        else:
            # Non-recursive: list immediate directory only
            files = []
            mp3_count = 0

            # Case-insensitive alphabetical sorting
            for file_path in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
                if file_path.is_file():
                    is_mp3 = file_path.suffix.lower() == '.mp3'
                    stat_info = file_path.stat()

                    file_info = FileInfo(
                        path=str(file_path),
                        name=file_path.name,
                        size=stat_info.st_size,
                        is_mp3=is_mp3,
                        metadata=None,  # Will load on demand
                        modified_time=stat_info.st_mtime,
                        created_time=stat_info.st_ctime
                    )

                    files.append(file_info)
                    if is_mp3:
                        mp3_count += 1

            total_files = len(files)

        # Save last_directory if remember feature is enabled (Task #84)
        try:
            from crate.core.config import load_config, set_config_value
            config = load_config()
            if config.get("remember_last_directory", True):
                set_config_value("last_directory", str(dir_path))
        except Exception as save_err:
            logger.warning(f"Failed to save last_directory: {save_err}")

        return DirectoryContents(
            path=str(dir_path),
            files=files,
            total_files=total_files,
            mp3_count=mp3_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing directory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# File metadata endpoint
@app.post("/api/file/metadata")
async def get_file_metadata(http_request: Request, request: DirectoryRequest):
    """
    Get metadata for a specific MP3 file.

    By default, this is a read-only operation (write_metadata=False).
    Set write_metadata=True to save enhanced BPM/Key back to disk.

    Supports cancellation: If client disconnects, processing will be cancelled
    at the next checkpoint (before MusicBrainz lookup or audio analysis).
    """
    try:
        # Check if client already disconnected (fast fail)
        if await http_request.is_disconnected():
            logger.info(f"[CANCEL] Client disconnected before processing: {request.path}")
            raise HTTPException(status_code=499, detail="Client disconnected")

        file_path = Path(request.path).expanduser().resolve()

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.path}")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {request.path}")

        # Create cancellation event for this request
        cancel_event = threading.Event()

        # Run analysis in thread pool with cancellation support
        async def analyze_with_cancel_check():
            # Start analysis in background thread
            task = asyncio.create_task(
                asyncio.to_thread(
                    renamer_api.analyze_file,
                    file_path,
                    request.write_metadata,
                    cancel_event
                )
            )

            # Periodically check if client disconnected
            while not task.done():
                if await http_request.is_disconnected():
                    logger.info(f"[CANCEL] Client disconnected during processing: {file_path.name}")
                    cancel_event.set()  # Signal cancellation to backend
                    # Wait a bit for graceful cancellation
                    try:
                        await asyncio.wait_for(task, timeout=0.5)
                    except asyncio.TimeoutError:
                        pass  # Backend will stop at next checkpoint
                    raise HTTPException(status_code=499, detail="Client disconnected")

                # Check every 100ms
                await asyncio.sleep(0.1)

            return await task

        metadata = await analyze_with_cancel_check()

        if metadata is None:
            raise HTTPException(status_code=400, detail="Could not read file metadata")

        return {
            "path": str(file_path),
            "name": file_path.name,
            "metadata": metadata
        }

    except OperationCancelled:
        logger.info(f"[CANCEL] Analysis cancelled: {request.path}")
        raise HTTPException(status_code=499, detail="Analysis cancelled")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Task #4: Album art endpoint
@app.get("/api/file/album-art")
async def get_album_art(file_path: str):
    """
    Extract and return album artwork from MP3 file.

    Task #4: Album cover art display

    Args:
        file_path: Path to MP3 file

    Returns:
        Image response with album artwork, or 404 if not found
    """
    from pathlib import Path as PathlibPath

    from fastapi.responses import Response

    from crate.core.io import extract_album_art

    try:
        path = PathlibPath(file_path)

        # Extract album art
        image_data, mime_type, error = extract_album_art(path, logger)

        if error:
            raise HTTPException(status_code=500, detail=error)

        if image_data is None:
            # No artwork found (not an error)
            raise HTTPException(status_code=404, detail="No album artwork found")

        # Return image with appropriate content type
        return Response(content=image_data, media_type=mime_type or "image/jpeg")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting album art: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Context analysis endpoint
@app.post("/api/analyze-context", response_model=AnalyzeContextResponse)
async def analyze_file_context(request: AnalyzeContextRequest):
    """
    Analyze file metadata to detect album vs singles context.

    Provides smart template suggestions based on detected context.
    Task #110: Supports per-album detection when feature flag enabled.
    """
    try:
        # Load config to check feature flag
        config = load_config()

        # Convert FileInfo models to dict format expected by analyzer
        files = [
            {
                "path": f.path,
                "name": f.name,
                "metadata": f.metadata or {}
            }
            for f in request.files
        ]

        # Task #110: Check if per-album detection is enabled
        per_album_enabled = config.get("enable_per_album_detection", False)
        logger.info(f"Per-album detection feature flag: {per_album_enabled}")

        if per_album_enabled:
            # Try per-album detection (requires directory parameter)
            # Extract directory from first file path
            if files and isinstance(files[0].get("path"), str):
                first_file_path = cast(str, files[0]["path"])
                directory = os.path.dirname(first_file_path)
                logger.info(f"Initial directory from first file: {directory}")

                # Find common parent directory if files from different subdirs
                for f in files[1:]:
                    f_path = f.get("path")
                    if isinstance(f_path, str) and f_path:
                        f_dir = os.path.dirname(f_path)
                        # Find common parent
                        while not f_dir.startswith(directory) and directory:
                            directory = os.path.dirname(directory)

                logger.info(f"Final common parent directory: {directory}")
                logger.info(f"Total files to analyze: {len(files)}")

                try:
                    # Use per-album detection
                    per_album_result = analyze_per_album_context(directory, files)

                    logger.info(f"Per-album detection result: per_album_mode={per_album_result.get('per_album_mode')}, albums={len(per_album_result.get('albums', []))}")

                    # If per-album mode is active, the frontend needs additional UI to support
                    # album-by-album selection/preview. For v0.1.0 we intentionally do not
                    # return per-album mode to avoid shipping a teased/unfinished UX.
                    if per_album_result.get("per_album_mode"):
                        logger.info("Per-album mode detected, but disabled for v0.1.0; falling back to single-banner")
                    else:
                        logger.info("✗ Per-album mode not activated (< 2 album groups), falling back to single-banner")
                except Exception as e:
                    logger.warning(f"Per-album detection failed, falling back to single mode: {e}", exc_info=True)
                    # Fall through to single-mode detection

        logger.info("Using single-banner mode (standard context detection)")

        # Standard single-mode detection (current behavior)
        contexts = analyze_context(files)

        # Convert contexts to response format
        context_responses = []
        for ctx in contexts:
            template_suggestions = [
                TemplateSuggestionResponse(
                    template=ts.template,
                    reason=ts.reason,
                    preset_id=ts.preset_id
                )
                for ts in ctx.suggested_templates
            ]

            context_responses.append(
                ContextAnalysisResponse(
                    type=ctx.type.value,
                    confidence=ctx.confidence,
                    album_name=ctx.album_name,
                    file_count=ctx.file_count,
                    track_range=ctx.track_range,
                    suggested_templates=template_suggestions,
                    warnings=ctx.warnings
                )
            )

        # Get default suggestion
        default_suggestion = get_default_suggestion(contexts)

        return AnalyzeContextResponse(
            contexts=context_responses,
            has_multiple_contexts=len(contexts) > 1,
            default_suggestion=default_suggestion,
        )

    except Exception as e:
        logger.error(f"Error analyzing context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _enforce_local_origin(request: Request) -> None:
    """Reject cross-site requests to state-changing endpoints.

    This app is meant to be used locally. If a user is tricked into visiting a
    malicious website, we don't want that site to be able to call our rename
    endpoints via the browser.

    We allow:
    - no Origin header (curl / non-browser clients)
    - http(s) origins whose hostname is localhost / 127.0.0.1

    Note: we intentionally do not allow arbitrary LAN hosts.
    """
    origin = request.headers.get("origin")
    if not origin:
        return

    try:
        parsed = urlparse(origin)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid Origin header")

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=403, detail="Disallowed Origin")

    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise HTTPException(status_code=403, detail="Disallowed Origin")


@app.get("/api/deps/status")
async def deps_status():
    """Report optional dependency status for local environment."""
    return {
        "platform": sys.platform,
        "brew": shutil.which("brew") is not None,
        "fpcalc": shutil.which("fpcalc") is not None,
    }


_chromaprint_install_lock = threading.Lock()


@app.post("/api/deps/chromaprint/install")
async def install_chromaprint(http_request: Request):
    """Install Chromaprint via Homebrew (macOS) with explicit user consent from UI."""
    _enforce_local_origin(http_request)

    if not _chromaprint_install_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Chromaprint install already in progress")

    if sys.platform != "darwin":
        raise HTTPException(status_code=400, detail="Chromaprint install is currently supported only on macOS")

    if shutil.which("fpcalc") is not None:
        _chromaprint_install_lock.release()
        return {"success": True, "message": "Chromaprint already installed", "command": "brew install chromaprint", "stdout": "", "stderr": "", "fpcalc": True}

    brew = shutil.which("brew")
    if not brew:
        _chromaprint_install_lock.release()
        raise HTTPException(status_code=400, detail="Homebrew not found. Install Homebrew first, then re-try.")

    try:
        r = subprocess.run(
            [brew, "install", "chromaprint"],
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )

        ok = (r.returncode == 0) and (shutil.which("fpcalc") is not None)
        msg = "Chromaprint installed" if ok else "Chromaprint install failed"
        return {
            "success": ok,
            "message": msg,
            "command": "brew install chromaprint",
            "returncode": r.returncode,
            "stdout": r.stdout[-20000:],
            "stderr": r.stderr[-20000:],
            "fpcalc": shutil.which("fpcalc") is not None,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Chromaprint install timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chromaprint install failed: {e}")
    finally:
        _chromaprint_install_lock.release()


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

        # Convert file paths to tuple if provided
        file_paths_tuple = None
        if request.file_paths:
            file_paths_tuple = tuple(Path(fp) for fp in request.file_paths)

        rename_request = RenameRequest(
            path=path,
            recursive=request.recursive,
            dry_run=True,  # Always dry run for preview
            template=request.template,
            auto_detect=request.enhance_metadata,  # Enable expensive metadata lookup if requested
            file_paths=file_paths_tuple  # Pass specific files if provided
        )

        previews = renamer_api.preview_rename(rename_request)

        # Convert to JSON-serializable format
        preview_list = [preview.to_dict() for preview in previews]

        # Calculate statistics
        will_rename = sum(1 for p in previews if p.status == "will_rename")
        will_skip = sum(1 for p in previews if p.status == "will_skip")
        errors = sum(1 for p in previews if p.status == "error")

        return {
            "path": str(path),
            "previews": preview_list,
            "total": len(preview_list),
            "stats": {
                "will_rename": will_rename,
                "will_skip": will_skip,
                "errors": errors
            }
        }

    except Exception as e:
        logger.error(f"Error generating preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Execute rename endpoint
@app.post("/api/rename/execute")
async def execute_rename(request: ExecuteRenameRequest, http_request: Request):
    _enforce_local_origin(http_request)
    """Execute rename operation on specific files."""
    try:
        path = Path(request.path).expanduser().resolve()

        if not request.file_paths:
            raise HTTPException(status_code=400, detail="No files specified for rename")

        # Validate and normalize provided paths (fail fast with clear UX messages).
        raw_paths = [str(fp).strip() for fp in request.file_paths if str(fp).strip()]
        mp3_paths = [Path(fp) for fp in raw_paths if fp.lower().endswith('.mp3')]

        if not mp3_paths:
            raise HTTPException(status_code=400, detail="No valid .mp3 files were provided")

        # Ensure selected files still exist.
        missing = [p for p in mp3_paths if not p.expanduser().exists()]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Selected file(s) no longer exist. Click Refresh and try again. Missing: {missing[0]}"
            )

        # Convert file paths to Path objects
        file_paths_tuple = tuple(mp3_paths)

        # Start async rename operation
        rename_request = RenameRequest(
            path=path,
            recursive=False,  # We're operating on specific files
            dry_run=request.dry_run,
            template=request.template,
            auto_detect=False,  # Don't re-analyze, use existing metadata
            file_paths=file_paths_tuple  # Pass specific files to rename
        )

        # Start async operation
        operation_id = renamer_api.start_rename_async(rename_request)

        return {
            "operation_id": operation_id,
            "status": "started",
            "message": "Rename operation started"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing rename: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Task #124: Streaming rename endpoint (Server-Sent Events)
@app.post("/api/rename/execute-stream")
async def execute_rename_stream(request: ExecuteRenameRequest, http_request: Request):
    _enforce_local_origin(http_request)
    """
    Execute rename with real-time progress streaming (Server-Sent Events).

    Task #124: Alternative to /api/rename/execute that streams progress.

    Benefits:
    - Real-time progress updates (no polling)
    - No HTTP timeout for large operations
    - Can cancel by closing EventSource
    - Better UX for massive libraries

    Returns:
        StreamingResponse with SSE events
    """
    try:
        path = Path(request.path).expanduser().resolve()

        if not request.file_paths:
            raise HTTPException(status_code=400, detail="No files specified for rename")

        # Validate and normalize provided paths (fail fast with clear UX messages).
        raw_paths = [str(fp).strip() for fp in request.file_paths if str(fp).strip()]
        mp3_paths = [Path(fp) for fp in raw_paths if fp.lower().endswith('.mp3')]

        if not mp3_paths:
            raise HTTPException(status_code=400, detail="No valid .mp3 files were provided")

        missing = [p for p in mp3_paths if not p.expanduser().exists()]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Selected file(s) no longer exist. Click Refresh and try again. Missing: {missing[0]}"
            )

        # Convert file paths to Path objects
        file_paths_tuple = tuple(mp3_paths)

        # Start async rename operation
        rename_request = RenameRequest(
            path=path,
            recursive=False,  # We're operating on specific files
            dry_run=request.dry_run,
            template=request.template,
            auto_detect=False,  # Don't re-analyze, use existing metadata
            file_paths=file_paths_tuple
        )

        # Start async operation
        operation_id = renamer_api.start_rename_async(rename_request)

        logger.info(f"Started streaming rename operation {operation_id} for {len(request.file_paths)} files")

        # Stream progress
        async def event_generator():
            async for chunk in stream_rename_progress(
                operation_id,
                len(request.file_paths),
                renamer_api,
                logger
            ):
                yield chunk

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting streaming rename: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Operation status endpoint
@app.get("/api/operation/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get status of an async operation."""
    try:
        status = renamer_api.get_operation_status(operation_id)

        if status is None:
            raise HTTPException(status_code=404, detail="Operation not found")

        # If operation completed successfully and we haven't created an undo session yet, create one
        if (status.status == "completed" and
            status.results and
            status.results.renamed > 0 and
            operation_id not in undo_sessions_created):

            # Extract successfully renamed files (status == "renamed")
            renamed_pairs = [
                (str(result.src), str(result.dst))
                for result in status.results.results
                if result.status == "renamed" and result.dst
            ]

            if renamed_pairs:
                # Create undo session with extended expiration (Task: Extend undo window)
                # Changed from 30 seconds to 10 minutes to accommodate large operations
                undo_session = UndoSession.create(pairs=renamed_pairs, expires_in_seconds=600)  # 10 minutes
                undo_sessions[undo_session.session_id] = undo_session
                undo_sessions_created.add(operation_id)

                logger.info(f"Created undo session {undo_session.session_id} for operation {operation_id} with {len(renamed_pairs)} files (expires in 10 minutes)")

                # Clean up expired sessions
                cleanup_expired_sessions()

                # Add session_id and expires_at to response
                response = status.to_dict()
                response["undo_session_id"] = undo_session.session_id
                response["undo_expires_at"] = undo_session.expires_at.isoformat()
                return response

        return status.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting operation status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Cancel operation endpoint
@app.post("/api/operation/{operation_id}/cancel")
async def cancel_operation(operation_id: str):
    """Cancel a running operation."""
    try:
        success = renamer_api.cancel_operation(operation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Operation not found or already complete")

        return {"success": True, "message": "Cancellation requested"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Undo rename endpoint
@app.post("/api/rename/undo")
async def undo_rename(session_id: str, http_request: Request):
    _enforce_local_origin(http_request)
    """
    Undo a previously executed rename operation.

    Args:
        session_id: Unique session ID from completed operation

    Returns:
        {
            "success": True,
            "reverted_count": 45,
            "error_count": 0,
            "errors": [],
            "message": "Successfully reverted 45 files"
        }

    Raises:
        HTTPException 404: Session expired or not found
        HTTPException 400: Files no longer exist or cannot be reverted
    """
    try:
        # Clean up expired sessions first
        cleanup_expired_sessions()

        # Check if session exists
        if session_id not in undo_sessions:
            raise HTTPException(
                status_code=404,
                detail="Undo session not found or expired (sessions expire after 10 minutes)"
            )

        session = undo_sessions[session_id]

        # Double-check expiration
        if session.is_expired():
            del undo_sessions[session_id]
            raise HTTPException(
                status_code=404,
                detail="Undo session expired (available for 10 minutes only)"
            )

        # Revert renames
        reverted = []
        errors = []

        for old_path, new_path in session.pairs:
            try:
                # Check if new file exists
                if not os.path.exists(new_path):
                    errors.append(f"File no longer exists: {new_path}")
                    continue

                # Check if old path is now occupied
                if os.path.exists(old_path):
                    errors.append(f"Cannot revert: original filename already exists: {old_path}")
                    continue

                # Revert the rename
                os.rename(new_path, old_path)
                reverted.append((new_path, old_path))
                logger.info(f"Reverted: {new_path} → {old_path}")

            except PermissionError:
                errors.append(f"Permission denied: {new_path}")
                logger.error(f"Permission denied reverting: {new_path}")
            except OSError as e:
                errors.append(f"Error reverting {new_path}: {str(e)}")
                logger.error(f"OS error reverting {new_path}: {e}")

        # Clean up session after use
        del undo_sessions[session_id]

        # Return results
        success = len(reverted) > 0
        message = f"Successfully reverted {len(reverted)} file{'s' if len(reverted) != 1 else ''}"

        if errors:
            if len(reverted) == 0:
                message = f"Failed to revert any files: {len(errors)} error{'s' if len(errors) != 1 else ''}"
            else:
                message += f", with {len(errors)} error{'s' if len(errors) != 1 else ''}"

        return {
            "success": success,
            "reverted_count": len(reverted),
            "error_count": len(errors),
            "errors": errors,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error undoing rename: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Configuration endpoints
@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    try:
        config = renamer_api.get_config()
        # Add first_run status to response
        config["is_first_run"] = is_first_run()
        return config
    except Exception as e:
        logger.error(f"Error getting config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/first-run")
async def check_first_run():
    """Check if this is the first run of the application."""
    try:
        first_run = is_first_run()
        config = renamer_api.get_config()

        # Check if API keys are configured (non-default values)
        acoustid_configured = config.get("acoustid_api_key") not in [None, "", "8XaBELgH"]

        return {
            "first_run": first_run,
            "keys_configured": acoustid_configured
        }
    except Exception as e:
        logger.error(f"Error checking first run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/complete-first-run")
async def complete_first_run():
    """Mark first run as complete."""
    try:
        success = mark_first_run_complete()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to mark first run complete")

        return {"success": True, "message": "First run marked as complete"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing first run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/defaults")
async def get_config_defaults():
    """Get default configuration values (not saved user config)."""
    try:
        from crate.core.config import DEFAULT_CONFIG
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Error getting defaults: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reset")
async def reset_config_to_defaults():
    """Reset configuration to defaults (preserves API keys and first_run status)."""
    try:
        from crate.core.config import DEFAULT_CONFIG, load_config, save_config
        current = load_config()
        reset = DEFAULT_CONFIG.copy()
        # Preserve user-specific values that shouldn't be reset
        reset["acoustid_api_key"] = current.get("acoustid_api_key", reset["acoustid_api_key"])
        reset["first_run_complete"] = current.get("first_run_complete", False)
        reset["last_directory"] = current.get("last_directory", "")
        success = save_config(reset)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset configuration")
        return {"success": True, "message": "Configuration reset to defaults", "config": reset}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting config: {e}", exc_info=True)
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


# =============================================================================
# NORMALIZATION API (Phase 1)
# =============================================================================


class NormalizeRequest(BaseModel):
    """Request to analyze/normalize audio files."""
    path: str
    mode: str = "analyze"  # analyze, tag, apply
    target_lufs: float = -11.5  # DJ standard (Platinum Notes default)
    recursive: bool = True


class NormalizeResult(BaseModel):
    """Result for a single file."""
    path: str
    success: bool
    original_lufs: Optional[float] = None
    original_peak_db: Optional[float] = None
    adjustment_db: Optional[float] = None
    clipping_prevented: bool = False
    error: Optional[str] = None


@app.post("/api/normalize")
async def normalize_files(request: NormalizeRequest):
    """Analyze or normalize audio files for consistent volume levels."""
    try:
        from crate.api.normalization import (
            NormalizationAPI,
            NormalizationMode,
            NormalizationRequest,
        )

        api = NormalizationAPI(logger=logger)

        # Map mode string to enum
        mode_map = {
            "analyze": NormalizationMode.ANALYZE,
            "tag": NormalizationMode.TAG,
            "apply": NormalizationMode.APPLY,
        }
        mode = mode_map.get(request.mode, NormalizationMode.ANALYZE)

        norm_request = NormalizationRequest(
            paths=[Path(request.path)],
            mode=mode,
            target_lufs=request.target_lufs,
            prevent_clipping=True,
            recursive=request.recursive,
        )

        status = api.normalize(norm_request)

        results = []
        for r in status.results:
            results.append({
                "path": str(r.path),
                "name": r.path.name,
                "success": r.success,
                "original_lufs": r.original_lufs,
                "original_peak_db": r.original_peak_db,
                "adjustment_db": r.adjustment_db,
                "clipping_prevented": r.clipping_prevented,
                "error": r.error,
            })

        return {
            "success": True,
            "total": status.total,
            "succeeded": status.succeeded,
            "failed": status.failed,
            "mode": request.mode,
            "target_lufs": request.target_lufs,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Normalization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CUE DETECTION API (Phase 2)
# =============================================================================


class CueDetectRequest(BaseModel):
    """Request to detect cue points."""
    path: str
    detect_intro: bool = True
    detect_drops: bool = True
    detect_breakdowns: bool = True
    sensitivity: float = 0.5
    max_cues: int = 8
    recursive: bool = True


class CueExportRequest(BaseModel):
    """Request to export cue points to Rekordbox XML."""
    results: list
    output_path: str


@app.post("/api/detect-cues")
async def detect_cues(request: CueDetectRequest):
    """Detect cue points (intro, drops, breakdowns) in audio files."""
    try:
        from crate.api.cue_detection import (
            CueDetectionAPI,
            CueDetectionRequest,
        )

        api = CueDetectionAPI(logger=logger)

        cue_request = CueDetectionRequest(
            paths=[Path(request.path)],
            detect_intro=request.detect_intro,
            detect_drops=request.detect_drops,
            detect_breakdowns=request.detect_breakdowns,
            max_cues=request.max_cues,
            sensitivity=request.sensitivity,
            recursive=request.recursive,
        )

        status = api.detect(cue_request)

        results = []
        for r in status.results:
            cues = []
            for cue in r.cues:
                cues.append({
                    "position_ms": cue.position_ms,
                    "position_str": f"{int(cue.position_ms // 60000)}:{(cue.position_ms % 60000) / 1000:05.2f}",
                    "type": cue.cue_type.value,
                    "confidence": cue.confidence,
                    "label": cue.label,
                    "hot_cue_index": cue.hot_cue_index,
                    "color": cue.color,
                })

            results.append({
                "path": str(r.path),
                "name": r.path.name,
                "success": r.success,
                "duration_ms": r.duration_ms,
                "bpm": r.bpm,
                "cues": cues,
                "error": r.error,
            })

        return {
            "success": True,
            "total": status.total,
            "succeeded": status.succeeded,
            "failed": status.failed,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Cue detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-cues")
async def export_cues(request: CueExportRequest):
    """Export detected cue points to Rekordbox XML format."""
    try:
        from crate.api.cue_detection import CueDetectionResult, CuePoint, CueType
        from crate.core.cue_detection import write_rekordbox_xml

        # Reconstruct CueDetectionResult objects from the request
        results = []
        for r in request.results:
            cues = []
            for c in r.get("cues", []):
                cue = CuePoint(
                    position_ms=c["position_ms"],
                    cue_type=CueType(c["type"]),
                    confidence=c.get("confidence", 1.0),
                    label=c.get("label"),
                    hot_cue_index=c.get("hot_cue_index"),
                    color=c.get("color"),
                )
                cues.append(cue)

            result = CueDetectionResult(
                path=Path(r["path"]),
                success=r["success"],
                cues=cues,
                duration_ms=r.get("duration_ms"),
                bpm=r.get("bpm"),
            )
            results.append(result)

        output_path = Path(request.output_path)
        write_rekordbox_xml(results, output_path, logger)

        return {
            "success": True,
            "output_path": str(output_path),
            "tracks_exported": len([r for r in results if r.success]),
        }

    except Exception as e:
        logger.error(f"Cue export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PEAK LIMITER ENDPOINTS
# =============================================================================


class LimitRequest(BaseModel):
    """Request to apply peak limiting to audio files."""
    path: str
    mode: str = "analyze"  # analyze, apply
    ceiling_percent: float = 99.7  # Platinum Notes default
    release_ms: float = 100.0
    recursive: bool = True


class LimitResult(BaseModel):
    """Result for a single file."""
    path: str
    name: str
    success: bool
    original_peak_db: Optional[float] = None
    limited_peak_db: Optional[float] = None
    reduction_db: Optional[float] = None
    samples_limited: int = 0
    error: Optional[str] = None


@app.post("/api/limit")
async def limit_files(request: LimitRequest):
    """Apply true peak limiting to audio files.
    
    Peak limiting prevents audio from exceeding a specified ceiling,
    which prevents clipping and distortion in playback systems.
    
    Default ceiling: 99.7% (-0.03 dB) per Platinum Notes DJ standard.
    """
    try:
        from crate.api.limiter import (
            LimiterAPI,
            LimiterMode,
            LimiterRequest,
        )

        api = LimiterAPI(logger=logger)

        # Map mode string to enum
        mode_map = {
            "analyze": LimiterMode.ANALYZE,
            "apply": LimiterMode.APPLY,
        }
        mode = mode_map.get(request.mode, LimiterMode.ANALYZE)

        limit_request = LimiterRequest(
            paths=[Path(request.path)],
            mode=mode,
            ceiling_percent=request.ceiling_percent,
            release_ms=request.release_ms,
            recursive=request.recursive,
        )

        status = api.limit(limit_request)

        results = []
        for r in status.results:
            results.append({
                "path": str(r.path),
                "name": r.path.name,
                "success": r.success,
                "original_peak_db": float(r.original_peak_db) if r.original_peak_db is not None else None,
                "limited_peak_db": float(r.limited_peak_db) if r.limited_peak_db is not None else None,
                "reduction_db": float(r.reduction_db) if r.reduction_db is not None else None,
                "samples_limited": r.samples_limited,
                "error": r.error,
            })

        return {
            "success": True,
            "total": status.total,
            "succeeded": status.succeeded,
            "failed": status.failed,
            "needed_limiting": status.needed_limiting,
            "mode": request.mode,
            "ceiling_percent": request.ceiling_percent,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Limiter error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PITCH CORRECTION ENDPOINTS
# =============================================================================


class PitchCorrectRequest(BaseModel):
    """Request to analyze/correct pitch in audio files."""
    path: str
    mode: str = "analyze"  # analyze, correct
    threshold_cents: float = 10.0  # Platinum Notes default
    recursive: bool = True


@app.post("/api/pitch-correct")
async def pitch_correct_files(request: PitchCorrectRequest):
    """Analyze or correct pitch in audio files.
    
    Detects pitch deviation from nearest semitone and optionally
    corrects audio to be in tune.
    
    Default threshold: 10 cents (per Platinum Notes).
    Default mode: analyze only (off by default).
    """
    try:
        from crate.api.pitch_correction import (
            PitchCorrectionAPI,
            PitchCorrectionMode,
            PitchCorrectionRequest,
        )

        api = PitchCorrectionAPI(logger=logger)

        # Map mode string to enum
        mode_map = {
            "analyze": PitchCorrectionMode.ANALYZE,
            "correct": PitchCorrectionMode.CORRECT,
        }
        mode = mode_map.get(request.mode, PitchCorrectionMode.ANALYZE)

        pitch_request = PitchCorrectionRequest(
            paths=[Path(request.path)],
            mode=mode,
            threshold_cents=request.threshold_cents,
            recursive=request.recursive,
        )

        status = api.process(pitch_request)

        results = []
        for r in status.results:
            results.append({
                "path": str(r.path),
                "name": r.path.name,
                "success": r.success,
                "original_pitch_hz": float(r.original_pitch_hz) if r.original_pitch_hz is not None else None,
                "corrected_pitch_hz": float(r.corrected_pitch_hz) if r.corrected_pitch_hz is not None else None,
                "shift_cents": float(r.shift_cents) if r.shift_cents is not None else None,
                "nearest_note": r.nearest_note,
                "error": r.error,
            })

        return {
            "success": True,
            "total": status.total,
            "succeeded": status.succeeded,
            "failed": status.failed,
            "needs_correction": status.needs_correction,
            "mode": request.mode,
            "threshold_cents": request.threshold_cents,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Pitch correction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon.ico (avoid browser 404 spam)."""
    ico_path = static_dir / "favicon.ico"
    if not ico_path.exists():
        raise HTTPException(status_code=404, detail="favicon.ico not found")
    return FileResponse(ico_path)


# Root endpoint - serve main HTML page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application page."""
    index_path = static_dir / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")

    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
