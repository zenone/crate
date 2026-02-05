# Crate Web API

Crate ships with a FastAPI-based web server (see `web/main.py`). This document summarizes the HTTP API and common workflows.

## Start the server

```bash
# from repo root
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-web.txt
python3 run_web.py
```

Default:
- UI: <http://127.0.0.1:8000/>
- OpenAPI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

## Conventions

- Most endpoints accept/return JSON.
- Long-running operations (analyze/rename) are tracked via an `operation_id`.
- Prefer **`/api/rename/execute-stream`** when you want live progress (SSE).

## Health

### GET `/api/health`
Simple health check.

Response:
```json
{"status":"ok"}
```

## Directory browsing

### POST `/api/directory/browse`
Browse directories (used by the UI file picker).

Request:
```json
{"path":"/Users/me/Music"}
```

### GET `/api/directory/initial`
Returns initial directory suggestions (e.g., last used directory, home, etc.).

### POST `/api/directory/list`
List contents of a directory.

Request:
```json
{"path":"/Users/me/Music/Incoming","recursive":false}
```

## File metadata

### POST `/api/file/metadata`
Reads metadata for a single file.

Request:
```json
{"path":"/Users/me/Music/Incoming/track.mp3"}
```

### GET `/api/file/album-art?path=...`
Returns embedded album art, if present.

## Context detection

### POST `/api/analyze-context`
Analyze a directory for album/EP/compilation context and grouping.

Request (example):
```json
{
  "path": "/Users/me/Music/Incoming",
  "recursive": true
}
```

## Templates

### POST `/api/template/validate`
Validate a filename template and return a sample expansion.

Request:
```json
{"template":"{artist} - {title} [{camelot} {bpm}]"}
```

## Rename workflow

### POST `/api/rename/preview`
Preview planned renames without changing files.

Request (minimal):
```json
{
  "path": "/Users/me/Music/Incoming",
  "recursive": true
}
```

Optional flags:
- `template`: override filename template
- `enhance_metadata`: run MusicBrainz + audio analysis enrichment
- `selected_files`: rename only a subset (paths)

### POST `/api/rename/execute`
Execute a rename operation (non-streaming). Returns an `operation_id`.

### POST `/api/rename/execute-stream`
Execute a rename operation and stream progress via Server-Sent Events (SSE).

Typical use:
- UI opens an SSE connection
- client receives progress events until completion

### GET `/api/operation/{operation_id}`
Poll operation status.

### POST `/api/operation/{operation_id}/cancel`
Cancel an in-progress operation.

### POST `/api/rename/undo`
Undo a previous rename operation.

## Config

### GET `/api/config`
Get current config.

### GET `/api/config/first-run`
Return first-run status.

### POST `/api/config/complete-first-run`
Mark first-run complete.

### POST `/api/config/update`
Update config.

---

## Notes for clients

- For exact request/response schemas, use the OpenAPI docs at `/docs`.
- If you only need CLI usage, see `README.md`.
