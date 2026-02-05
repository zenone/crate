# CLI Guide

Crate’s CLI is designed for safe batch operations.

## Preview first (recommended)

```bash
crate ~/Music/DJ/Incoming --recursive --dry-run -v
```

## Apply renames

```bash
crate ~/Music/DJ/Incoming --recursive
```

## Deep scan (BPM/Key detection)

Use this when BPM/Key tags are missing.

```bash
crate ~/Music/DJ/Incoming --recursive --analyze
```

## Template override

```bash
crate ~/Music/DJ/Incoming --recursive --dry-run \
  --template "{artist} - {title} [{camelot} {bpm}]"
```

## Troubleshooting

- If you see “No .mp3 files found”: confirm you pointed at a folder containing MP3s.
- If analysis is “Unavailable”: install optional audio deps (see `INSTALLATION.md`).
