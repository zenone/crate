# 📦 Crate

**The DJ's Indestructible Library Tool**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/zenone/crate)
[![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-389%20passed-success.svg)](https://github.com/zenone/crate)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

A **DJ-first MP3 renaming and metadata cleanup tool** designed for real-world workflows:

- **Rekordbox** / **Pioneer CDJ-3000** / **XDJ gear**
- USB export + Finder browsing
- Long-term library hygiene and portability

**Crate** focuses on what actually matters to DJs:

- Human-readable, scan-friendly filenames (`Artist - Title [8A 128]`)
- Clean, deterministic metadata
- Album/EP ordering that *never breaks*
- Optional audio analysis for untagged files

---

## ✨ What Crate Does

### Screenshots

Web UI (directory picker):

![Crate Web UI](docs/assets/screenshots/web-ui-directory-select.webp)

Web UI (preview):

![Crate Web Preview](docs/assets/web-preview.png)

CLI (dry-run):

![Crate CLI](docs/assets/cli.png)

### Smart DJ-Friendly Filenames

Creates filenames like:

```
Artist - Track Title (Extended Mix) [8A 128].mp3
01 Artist - Track Title.mp3
```

Why this works:
- **Artist - Title first** → fastest scanning on CDJs & USBs
- Optional **Camelot Key + BPM** for instant context
- **Track numbers preserved** for albums/EPs

### Deep Metadata Reading

Reads metadata from **all common DJ tag variants**:
- Standard ID3 frames (`TPE1`, `TIT2`, `TALB`, `TBPM`, `TKEY`)
- Rekordbox/Serato custom tags
- Fallback to filename parsing if tags are missing

### Album / EP Detection

When processing folders:
- If **all tracks share the same album tag** and **most have track numbers**
- ➡️ Crate automatically prefixes `01`, `02`...

---

## 🚀 Quick Start

### Install

```bash
# Clone and install
git clone https://github.com/zenone/crate.git
cd crate
pip install -e .
```

### First Run (Safe Mode)

```bash
# Dry run - shows what WOULD change (no actual changes)
crate ~/Music/Incoming --recursive --dry-run -v
```

### Rename Files

```bash
# Actually rename files
crate ~/Music/Incoming --recursive
```

### Web Interface

```bash
# Start the web UI
make web
# Then open http://127.0.0.1:8000
```

---

## 💻 Web Interface

The modern Web UI offers:

- **Directory Browser** - navigate your filesystem
- **Live Preview** - see changes before applying
- **Dark Mode** - because we're DJs
- **Undo** - one-click revert
- **Drag & Drop** - upload files directly

```bash
./crate-web.sh --no-https
```

API docs: http://localhost:8000/docs

---

## 🎚️ CLI Examples

### Single file
```bash
crate "Unknown Track.mp3"
```

### Recursive folder (label dumps)
```bash
crate ~/Music/NewTracks --recursive
```

### With Key & BPM (default template)
```bash
crate ~/Music/NewTracks
# Output: Artist - Track Title [8A 128].mp3
```

### Audio analysis for untagged files
```bash
# Slower but finds BPM/key from audio
crate ~/Music/Untagged --analyze
```

---

## ⚙️ CLI Options

```
crate PATH [options]

positional arguments:
  path                  File or directory to process

options:
  -h, --help            Show help message
  --recursive           Recurse into subfolders
  --dry-run             Show changes without applying
  --workers WORKERS     Number of worker threads (default: 4)
  -l, --log LOG         Write detailed log to file
  -v                    Increase verbosity (-v, -vv)
  --template TEMPLATE   Filename template
                        Default: '{artist} - {title}{mix_paren}{kb}'
  --analyze             Enable audio analysis for BPM/key detection
```

---

## 🛠️ Development

### Setup

```bash
# Create venv and install dev deps
make setup
source .venv/bin/activate
```

### Testing

```bash
make test          # Unit tests (fast)
make golden        # Integration tests with real MP3s
make verify        # Full quality gate (lint + test)
```

### Code Quality

```bash
make lint          # ruff + mypy
make format        # Auto-format with ruff
```

### Project Structure

```
crate/
├── crate/          # Core library
│   ├── api/        # Python API
│   ├── cli/        # CLI interface
│   └── core/       # Business logic
├── web/            # Web UI (FastAPI)
├── tests/          # Test suite (389+ tests)
└── docs/           # Documentation
```

---

## 📦 Installation Details

**Requirements:** Python 3.10+

```bash
pip install -e .
```

For audio analysis (optional):
- macOS: `brew install chromaprint`
- Linux: `apt install libchromaprint-tools`

Full guide: [INSTALLATION.md](INSTALLATION.md)

---

## 🛡️ Philosophy

Crate is opinionated on purpose. It favors **Stability** over cleverness and **Human Readability** over database purity.

If your USB ever corrupts, Rekordbox breaks, or you switch platforms —  
**your library will still make sense.**

---

## 👤 About

Built by [Steve Zenone](https://www.linkedin.com/in/zenone/).

---

## 🖤 Built for DJs who care about their libraries.
