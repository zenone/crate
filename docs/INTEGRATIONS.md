# Integrations

This repo supports two integration styles:

1) **HTTP / Web API** (for web UIs, scripts, other languages)
2) **Python API** (import and call directly)

## 1) HTTP / Web API

Start server:

```bash
python3 run_web.py
```

- OpenAPI: http://localhost:8000/docs
- Human summary: `docs/API.md`

Typical workflow:
- `POST /api/rename/preview`
- `POST /api/rename/execute-stream` (SSE)
- `POST /api/rename/undo`

## 2) Python API

```python
from pathlib import Path
from crate.api import RenamerAPI, RenameRequest

api = RenamerAPI(workers=4)
request = RenameRequest(
    path=Path.home() / "Music/DJ/Incoming",
    recursive=True,
    dry_run=True,
)
status = api.rename_files(request)
print(status.total, status.renamed, status.skipped, status.errors)
```

Notes:
- Use `dry_run=True` first.
- Templates are described in `TEMPLATE_VARIABLES.md`.
