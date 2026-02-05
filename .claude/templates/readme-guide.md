# README Writing Guide

## Philosophy

A great README is **marketing + documentation + onboarding** in one file.

If people don't read your README, they won't use your project.
If they read it but don't understand it, they'll leave.
Make it **enjoyable to read**.

---

## Structure (Recommended Order)

### 1. Title + One-Liner (5 seconds)
```markdown
# ProjectName 🎯

One sentence: what it does, who it's for.
```

**Good**: "Smart DJ-friendly MP3 renaming and metadata cleanup tool."
**Bad**: "A tool for files."

### 2. Hero Section (30 seconds)
- Screenshot or GIF of the tool in action
- Or a compelling code example
- Or the key benefit in bold

```markdown
![Demo](docs/demo.gif)

**Stop manually renaming 500 MP3s. Let Crate do it in 5 seconds.**
```

### 3. Quick Start (2 minutes)
```markdown
## Quick Start

```bash
pip install crate
crate ~/Music/Incoming --dry-run
```

That's it. Your files are now perfectly named.
```

Get them to success **fast**. Details come later.

### 4. Features (Scannable)
```markdown
## Features

- 🎧 **DJ-friendly names**: `Artist - Title [8A 128 BPM].mp3`
- 🔍 **Preview mode**: See changes before applying
- ↩️ **Undo**: Made a mistake? One command to revert
- 🌐 **Web UI**: Drag-and-drop interface
```

Use emojis sparingly. Make it scannable.

### 5. Installation (All Options)
```markdown
## Installation

### pip (recommended)
```bash
pip install crate
```

### Homebrew
```bash
brew install crate
```

### From source
```bash
git clone ...
pip install -e .
```
```

### 6. Usage Examples (Real Scenarios)
```markdown
## Usage

### Basic rename
```bash
crate ~/Music/Incoming
```

### Preview without changing anything
```bash
crate ~/Music/Incoming --dry-run -vv
```

### Process entire library
```bash
crate ~/Music --recursive
```
```

Show **real commands** people will actually use.

### 7. Configuration (If Applicable)
```markdown
## Configuration

Create `~/.crate/config.json`:
```json
{
  "template": "{artist} - {title} [{key} {bpm} BPM]",
  "dry_run": false
}
```
```

### 8. FAQ / Troubleshooting
```markdown
## FAQ

### Why doesn't it detect the key?
The key must be in the file's metadata. Run `crate --verbose` to see what tags are found.

### Can I undo a rename?
Yes! Run `crate undo` within 24 hours of the operation.
```

### 9. Contributing
```markdown
## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
```

### 10. License
```markdown
## License

MIT. See [LICENSE](LICENSE).
```

---

## Writing Style

### Be Conversational
❌ "The application provides functionality for..."
✅ "This tool helps you..."

### Be Specific
❌ "Fast performance"
✅ "Processes 10,000 files in under 30 seconds"

### Be Honest
❌ "Works with any audio file"
✅ "Supports MP3 files. FLAC support coming in v2."

### Be Scannable
- Use headers liberally
- Use bullet points
- Use code blocks
- Use bold for key terms
- Keep paragraphs short (3-4 lines max)

### Be Accessible
Write for:
- **Non-technical users**: Explain what, not how
- **New developers**: Show copy-paste examples
- **Experts**: Link to advanced docs

---

## Entertaining READMEs

### Add Personality
```markdown
## Why Crate?

Because "Unknown Artist - Track 01.mp3" is not a vibe.

Your DJ library deserves better. Crate reads metadata from your files
and generates clean, scannable filenames that look great on CDJs,
in Finder, and everywhere else.

No more squinting. No more guessing. Just clean names.
```

### Use Relatable Examples
```markdown
## Before & After

**Before**:
```
01_-_Unknown_Artist_-_track.MP3
song (1).mp3
FINAL_FINAL_v2.mp3
```

**After**:
```
Bicep - Glue (Original Mix) [11A 130 BPM].mp3
Fred Again.. - Delilah (Pull Me Out of This) [4A 138 BPM].mp3
Disclosure - Latch ft. Sam Smith (Extended Mix) [2B 122 BPM].mp3
```

*chef's kiss* 👨‍🍳
```

### Anticipate Questions
```markdown
## "But what if..."

**"What if I don't like the changes?"**
Preview first with `--dry-run`. Nothing gets renamed until you're ready.

**"What if it messes up my files?"**
It won't. Crate never overwrites—collisions become `Track (2).mp3`.
Plus, everything's undoable.

**"What if my metadata is garbage?"**
Crate handles it. Missing artist? It falls back to filename parsing.
Wrong key? Run with `--skip-key` to leave it out.
```

---

## Checklist

Before publishing:

- [ ] Title + one-liner is compelling
- [ ] Screenshot or GIF shows the tool in action
- [ ] Quick start gets to "hello world" in <2 minutes
- [ ] Examples use real, relatable scenarios
- [ ] Installation instructions are copy-paste-able
- [ ] FAQ addresses common questions
- [ ] No broken links
- [ ] No outdated information
- [ ] No AI-generated filler ("Certainly!", "Great question!")
- [ ] Proofread for typos
- [ ] Tested every code example

---

## Anti-Patterns

❌ **Wall of text**: No one reads 10 paragraphs before seeing what the tool does.

❌ **Missing examples**: "See documentation" without showing anything.

❌ **Jargon overload**: "Leveraging synergies through paradigm shifts..."

❌ **Outdated badges**: Broken CI badges are worse than no badges.

❌ **No quick start**: Making people read 500 words before `pip install`.

❌ **Lying**: "Fast" when it's slow. "Easy" when it's complex. People notice.

---

*A README is the front door to your project. Make it inviting.*
