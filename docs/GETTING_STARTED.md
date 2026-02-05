# Getting Started (DJs & Producers)

Crate helps you clean up and rename MP3s into **DJ-friendly filenames** (fast to scan on USBs / CDJs) while keeping everything **safe and reversible**.

If you’re not technical: start here.

---

## 0) The “safest” way to use Crate

Crate is designed around a simple rule:

1) **Preview first** (no changes)
2) **Rename** (apply changes)
3) **Undo** if needed

This makes it hard to accidentally mess up a library.

---

## 1) Put tracks in a simple folder

Most DJs have a “new downloads / to process” folder. We’ll use:

- `~/Music/DJ/Incoming`

Put a few MP3s in there to start.

---

## 2) Install

### macOS / Linux

```bash
cd /path/to/crate
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Windows

Use PowerShell:

```powershell
cd C:\path\to\crate
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 3) Run the Web UI (recommended)

```bash
python3 run_web.py
```

Open:
- http://localhost:8000

Then:
1) Select your folder (e.g. `~/Music/DJ/Incoming`)
2) Click **Preview**
3) If it looks right, click **Rename**
4) If you regret it, click **Undo**

---

## 4) CLI (for power users)

### Preview only (dry run)

```bash
crate ~/Music/DJ/Incoming --recursive --dry-run -v
```

### Apply rename

```bash
crate ~/Music/DJ/Incoming --recursive
```

---

## 5) When do I need “Analyze”?

By default, Crate is fast: it uses whatever is already in ID3 tags.

If your tracks are missing BPM/Key tags, run a slower but smarter pass:

```bash
crate ~/Music/DJ/Incoming --recursive --analyze
```

---

## Rekordbox note (important)

Rekordbox **USB exports** typically use a managed device folder structure (not your original folders). Because of that, Crate is usually best used:

- **Before** exporting to USB (on your computer’s music folders), or
- On a **prep folder** like `~/Music/DJ/Incoming` that you later import/export from Rekordbox.

---

## Next steps

- Templates & variables: see `TEMPLATE_VARIABLES.md`
- Web API reference: see `docs/API.md` or http://localhost:8000/docs
- Full manual testing: `MANUAL_TESTING.md`
