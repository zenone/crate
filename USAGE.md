# Usage

Quick reference for common Crate operations.

## CLI

### Basic rename (dry run first!)
```bash
crate ~/Music/NewTracks --dry-run -v
crate ~/Music/NewTracks
```

### Recursive processing
```bash
crate ~/Music/Incoming --recursive
```

### Audio analysis (slow but thorough)
```bash
crate ~/Music/Untagged --analyze
```

### Custom template
```bash
crate ~/Music/Tracks --template "{bpm} - {artist} - {title}"
```

## Web UI

```bash
make web
# Then open http://127.0.0.1:8000
```

Or manually:
```bash
./crate-web.sh              # HTTPS (default)
./crate-web.sh --no-https   # HTTP mode
./crate-web.sh --open       # Auto-open browser
```

## Development

```bash
make setup    # Create venv + install deps
make test     # Run unit tests
make golden   # Run integration tests (real MP3s)
make verify   # Full quality gate
make lint     # ruff + mypy
make format   # Auto-format
```

## Template Variables

| Variable | Description |
|----------|-------------|
| `{artist}` | Artist name |
| `{title}` | Track title |
| `{bpm}` | BPM |
| `{key}` | Musical key (Am, Gm) |
| `{camelot}` | Camelot notation (8A, 9B) |
| `{mix}` | Mix version |
| `{mix_paren}` | Mix in parentheses |
| `{kb}` | Key + BPM in brackets |
| `{track}` | Track number |

Default template: `{artist} - {title}{mix_paren}{kb}`

## More Info

- [Getting Started](docs/GETTING_STARTED.md)
- [API Reference](docs/API.md)
- [CLI Reference](docs/CLI.md)
- [Installation](INSTALLATION.md)
