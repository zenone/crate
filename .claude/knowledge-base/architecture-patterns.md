# Architecture Patterns

Proven patterns from shipped projects. Use these as starting points.

---

## API-First Architecture

**When**: Any project with multiple interfaces (web + CLI, API + UI).

**Structure**:
```
src/
├── api/           # Business logic (tested, reusable)
│   ├── __init__.py
│   ├── auth.py
│   └── users.py
├── web/           # Web UI (consumes API)
│   ├── routes.py
│   └── templates/
├── cli/           # CLI (consumes API)
│   └── main.py
└── core/          # Low-level utilities (API only imports this)
    └── utils.py
```

**Rules**:
- UI layers (`web/`, `cli/`) ONLY import from `api/`
- Never import `core/` directly in UI layers
- Same logic, tested once, consistent behavior everywhere

**Benefits**:
- Single source of truth for business logic
- Easy to add new interfaces (mobile, SDK, etc.)
- Tests cover business logic once, not per-interface

---

## Daemon + Job Queue (Privileged Operations)

**When**: App needs sudo/root operations but shouldn't run entirely as root.

**Implementation**:
```
/var/local/appname-jobs/     # Job queue directory
/Library/LaunchDaemons/com.appname.daemon.plist  # macOS daemon
/etc/systemd/system/appname-daemon.service       # Linux daemon
```

**Job File Format** (JSON):
```json
{
  "id": "uuid",
  "operation": "clean_system_cache",
  "params": {"path": "/Library/Caches"},
  "status": "pending",
  "created_at": "2026-02-01T10:00:00Z"
}
```

**Daemon Loop**:
```python
while True:
    for job_file in sorted(job_dir.glob("*.json")):
        job = json.loads(job_file.read_text())
        if job["status"] == "pending":
            result = execute_privileged_operation(job)
            job["status"] = "completed"
            job["result"] = result
            job_file.write_text(json.dumps(job))
    sleep(1)
```

**Benefits**:
- No password prompts in UI
- Clean audit trail (job files)
- App can run unprivileged; daemon handles elevated ops

---

## Preview Mode Pattern

**When**: Any destructive or modifying operation.

**Implementation**:
```python
def clean_files(paths: list[Path], preview: bool = False) -> CleanResult:
    """Clean files with optional preview mode."""
    result = CleanResult()
    
    for path in paths:
        if path.exists():
            result.add_file(path, path.stat().st_size)
            if not preview:
                path.unlink()
    
    return result
```

**CLI**:
```bash
app clean --preview   # Shows what would be deleted
app clean             # Actually deletes
```

**Benefits**:
- Users trust tools that show before doing
- Same code path = no divergence bugs between preview and real mode
- Great for debugging ("why did it delete X?")

---

## State Files Over Memory

**When**: Any stateful application.

**Pattern**:
```
~/.appname/
├── config.json      # User preferences
├── history.json     # Operation history
└── cache/           # Cached data
```

**Rules**:
- If it matters tomorrow, write it to disk today
- JSON for human-readable config; SQLite for structured data
- Agent/session memory doesn't persist—state files do

**Example Config**:
```python
CONFIG_PATH = Path.home() / ".appname" / "config.json"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return DEFAULT_CONFIG

def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
```

---

## Kill Feature Criteria

**When**: A feature has persistent bugs across multiple sessions.

**Rule**: If a feature has **3+ debugging sessions** without resolution, consider cutting it.

**Decision Framework**:
1. How critical is this feature to the core product?
2. Is there an alternative (e.g., web UI instead of TUI)?
3. What's the maintenance cost of keeping buggy code?
4. A polished single interface > buggy multiple interfaces

**Example**: Upkeep v2.0 removed 2,054 lines of TUI code after persistent layout/async bugs. Web UI was sufficient.

---

## TypeScript for Web Frontends

**When**: Any JavaScript over ~200 lines.

**Setup** (5 minutes):
```bash
npm init -y
npm install -D typescript esbuild
```

**tsconfig.json**:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,
    "outDir": "./dist",
    "rootDir": "./src"
  }
}
```

**Build**:
```bash
npx esbuild src/main.ts --bundle --outfile=dist/bundle.js
```

**Benefits**:
- Types catch bugs during refactoring
- IDE autocomplete and error checking
- Minimal setup cost, big payoff

---

## Cross-Machine Coordination (Event Bus)

**When**: Multiple instances need to coordinate (e.g., iMac ↔ MacBook).

**Structure**:
```
shared-directory/         # Dropbox, iCloud, or network share
├── state/
│   └── status/          # Current status per host
│       ├── host-a.json
│       └── host-b.json
├── events/
│   ├── jobs/            # Pending work items
│   ├── receipts/        # Completed job results
│   └── jobs-archive/    # Processed jobs (ok/skipped/failed)
└── mailbox/             # Direct messages between hosts
    ├── host-a/          # Messages TO host-a
    └── host-b/          # Messages TO host-b
```

**Status File Format**:
```json
{
  "host": "imac",
  "updatedAt": "2026-02-05T12:00:00Z",
  "currentProject": "ai-dev-kit",
  "needsAttention": [],
  "lastJobResult": null
}
```

**Job File Format**:
```json
{
  "id": "job-20260205-1200-task-name",
  "targetHost": "macbook",
  "action": "sync",
  "params": {"source": "~/Code/", "dest": "~/Code/"},
  "requiresHumanGo": false,
  "createdAt": "2026-02-05T12:00:00Z"
}
```

**Key Patterns**:
- **Claim before execute**: Rename job file with `.claimed-by-{host}` extension
- **Idempotent jobs**: Jobs can be retried safely
- **Fixed result paths**: Use predictable filenames to avoid Dropbox dir listing issues
- **Human-gated jobs**: `requiresHumanGo: true` for risky operations

---

## Configuration Layering

**Pattern**: Multiple config sources with clear precedence.

**Precedence (highest to lowest)**:
1. Command-line arguments
2. Environment variables
3. User config file (`~/.appname/config.json`)
4. Project config file (`.appname.json` in cwd)
5. System config (`/etc/appname/config.json`)
6. Hardcoded defaults

**Implementation**:
```python
from dataclasses import dataclass, field
from pathlib import Path
import os
import json

@dataclass
class Config:
    api_url: str = "https://api.example.com"
    timeout: int = 30
    debug: bool = False

def load_config() -> Config:
    config = Config()
    
    # Layer 5: System config
    system_config = Path("/etc/appname/config.json")
    if system_config.exists():
        config = merge_config(config, json.loads(system_config.read_text()))
    
    # Layer 4: Project config
    project_config = Path.cwd() / ".appname.json"
    if project_config.exists():
        config = merge_config(config, json.loads(project_config.read_text()))
    
    # Layer 3: User config
    user_config = Path.home() / ".appname" / "config.json"
    if user_config.exists():
        config = merge_config(config, json.loads(user_config.read_text()))
    
    # Layer 2: Environment variables
    if os.getenv("APPNAME_API_URL"):
        config.api_url = os.environ["APPNAME_API_URL"]
    if os.getenv("APPNAME_TIMEOUT"):
        config.timeout = int(os.environ["APPNAME_TIMEOUT"])
    if os.getenv("APPNAME_DEBUG"):
        config.debug = os.environ["APPNAME_DEBUG"].lower() == "true"
    
    # Layer 1: CLI args handled at call site
    return config
```

---

## Error Boundary Pattern

**When**: Preventing one failure from crashing the entire system.

**Implementation**:
```python
from typing import Callable, TypeVar, Optional
from dataclasses import dataclass
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)

@dataclass
class Result[T]:
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None

def error_boundary(operation: str) -> Callable:
    """Decorator that catches exceptions and returns Result."""
    def decorator(func: Callable[..., T]) -> Callable[..., Result[T]]:
        def wrapper(*args, **kwargs) -> Result[T]:
            try:
                value = func(*args, **kwargs)
                return Result(success=True, value=value)
            except Exception as e:
                logger.error(f"{operation} failed: {e}", exc_info=True)
                return Result(success=False, error=str(e))
        return wrapper
    return decorator

# Usage
@error_boundary("user_sync")
def sync_user(user_id: int) -> dict:
    # ... might raise exceptions ...
    return {"synced": True}

# Caller handles gracefully
result = sync_user(123)
if result.success:
    print(f"Synced: {result.value}")
else:
    print(f"Failed: {result.error}")
    # Continue with other users instead of crashing
```

---

## Retry with Exponential Backoff

**When**: Network requests, external APIs, distributed systems.

```python
import time
import random
from typing import TypeVar, Callable

T = TypeVar('T')

def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> T:
    """Retry function with exponential backoff."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries - 1:
                break
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay *= (0.5 + random.random())  # 50-150% of delay
            
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
            time.sleep(delay)
    
    raise last_exception

# Usage
result = retry_with_backoff(
    lambda: api_client.fetch("/users"),
    max_retries=5,
    base_delay=2.0
)
```

---

## Graceful Degradation

**Pattern**: System continues working with reduced functionality when components fail.

```python
class FeatureFlags:
    """Track which features are available."""
    
    def __init__(self):
        self.available = {}
    
    def check(self, feature: str, check_func: Callable[[], bool]) -> bool:
        """Check if feature is available, cache result."""
        if feature not in self.available:
            try:
                self.available[feature] = check_func()
            except Exception:
                self.available[feature] = False
        return self.available[feature]

flags = FeatureFlags()

# Usage
def get_user_avatar(user_id: int) -> str:
    if flags.check("image_service", lambda: image_service.ping()):
        return image_service.get_avatar(user_id)
    else:
        # Graceful degradation: return default avatar
        return "/static/default-avatar.png"
```
