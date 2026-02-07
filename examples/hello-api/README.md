# Hello API - Example Project

A minimal example showing the template in action.

## Structure

```
hello-api/
├── CLAUDE.md           # dev guidance (from template)
├── .claude/            # dev memory (from template)
├── src/
│   ├── core/           # Business logic
│   │   └── greeter.py
│   └── api/            # API layer
│       └── routes.py
├── tests/
│   └── test_greeter.py
└── pyproject.toml
```

## Key Patterns Demonstrated

1. **API-First Architecture**: `core/` has no web dependencies, `api/` is thin wrapper
2. **TDD**: Tests written first, implementation follows
3. **State Tracking**: `.claude/state/current-state.md` updated after changes

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Test
pytest

# Run
uvicorn src.api.routes:app --reload
```

## API Endpoints

- `GET /` - Health check
- `GET /greet/{name}` - Returns personalized greeting
- `POST /greet` - Custom greeting with options
