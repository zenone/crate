# Template Variables Reference

**DJ MP3 Renamer - Template System Guide**

---

## Philosophy

Template variables follow best practices:
- ✅ **Descriptive names** - Self-explanatory, no cryptic abbreviations
- ✅ **Atomic values** - One piece of data per variable
- ✅ **User controls formatting** - You add parentheses, brackets, spacing
- ✅ **Consistent naming** - All lowercase, underscores for multi-word
- ✅ **DJ-focused** - Uses terminology DJs understand

---

## Available Variables

### Core Metadata

| Variable | Description | Example | Always Present |
|----------|-------------|---------|----------------|
| `{artist}` | Artist or band name | "Daft Punk" | ✓ (defaults to "Unknown Artist") |
| `{title}` | Song title (mix removed if detected) | "One More Time" | ✓ (defaults to "Unknown Title") |
| `{album}` | Album name | "Discovery" | If in tags |
| `{label}` | Record label | "Virgin Records" | If in tags |
| `{year}` | Release year | "2001" | If in tags |
| `{track}` | Track number (zero-padded) | "04" | If in tags |

### DJ-Specific

| Variable | Description | Example | Always Present |
|----------|-------------|---------|----------------|
| `{bpm}` | Beats per minute | "125" | If in tags or detected |
| `{key}` | Musical key | "F# min" | If in tags or detected |
| `{camelot}` | Camelot wheel notation | "11A" | If key available |
| `{mix}` | Remix/mix version | "Radio Edit" | If detected in title |

---

## Default Template

```
{artist} - {title} [{camelot} {bpm}]
```

**Examples:**
- `Daft Punk - One More Time [6B 123].mp3`
- `Justice - Genesis [7A 130].mp3`
- `Deadmau5 - Strobe (Original Mix) [1A 128].mp3`

---

## Template Examples

### Minimal (Artist - Title only)
```
{artist} - {title}
```
Result: `Daft Punk - One More Time.mp3`

### With Key and BPM
```
{artist} - {title} [{camelot} {bpm}]
```
Result: `Daft Punk - One More Time [6B 123].mp3`

### BPM First (for sorting)
```
{bpm} - {artist} - {title}
```
Result: `123 - Daft Punk - One More Time.mp3`

### With Mix Name
```
{artist} - {title} ({mix}) [{camelot} {bpm}]
```
Result: `Daft Punk - One More Time (Radio Edit) [6B 123].mp3`

### Track Number Prefix
```
{track} {artist} - {title} [{camelot} {bpm}]
```
Result: `04 Daft Punk - One More Time [6B 123].mp3`

### Full Metadata
```
{artist} - {title} ({mix}) [{key} {bpm}] - {album} ({year})
```
Result: `Daft Punk - One More Time (Radio Edit) [F# min 123] - Discovery (2001).mp3`

---

## Formatting Tips

### Empty Variables Behavior
- Empty variables produce empty strings (no placeholder text)
- Extra spaces are automatically cleaned up by the sanitizer
- Empty parentheses/brackets `()` or `[]` are NOT automatically removed

**Example:**
```
{artist} - {title} [{camelot} {bpm}]
```
If BPM is missing: `Artist - Title [7A ].mp3` (extra space before `]`)

**Solution:** Only include brackets if you know BPM exists, or accept minor formatting quirks.

### Spacing
- Add spaces explicitly: `{artist} - {title}` (spaces around `-`)
- Don't rely on variables to include spaces

### Special Characters
- Parentheses: `()` for mix names
- Brackets: `[]` for DJ info (key/BPM)
- Hyphens: `-` for separators
- Underscores: `_` for word separators (less common)

---

## Variable Details

### `{artist}`
- **Source**: ID3 tag TPE1
- **Default**: "Unknown Artist" if missing
- **Sanitized**: Yes (removes illegal filename characters)

### `{title}`
- **Source**: ID3 tag TIT2
- **Default**: "Unknown Title" if missing
- **Mix Removed**: Yes, if `{mix}` detected (e.g., "Song (Remix)" → "Song")
- **Sanitized**: Yes

### `{bpm}`
- **Source**: ID3 tag TBPM or auto-detected
- **Format**: Integer string (e.g., "128")
- **Range**: 60-200 (typical DJ range)
- **Auto-detection**: Yes, if missing and enabled
- **Empty if**: Not in tags and detection disabled

### `{key}`
- **Source**: ID3 tag TKEY or auto-detected
- **Format**: Standard notation (e.g., "F# min", "C maj")
- **Auto-detection**: Yes, if missing and enabled
- **Empty if**: Not in tags and detection disabled

### `{camelot}`
- **Source**: Converted from `{key}`
- **Format**: Camelot wheel notation (e.g., "7A", "11B")
- **Empty if**: No key available

### `{mix}`
- **Source**: Inferred from title
- **Detection**: Looks for patterns like "(Remix)", "[Edit]", "- Mix"
- **Examples**: "Radio Edit", "Extended Mix", "Dub Version"
- **Empty if**: No mix detected

### `{year}`
- **Source**: ID3 tag TDRC or TYER
- **Format**: 4-digit year (e.g., "2024")
- **Empty if**: Not in tags

### `{album}`
- **Source**: ID3 tag TALB
- **Empty if**: Not in tags

### `{label}`
- **Source**: ID3 tag TPUB
- **Empty if**: Not in tags

### `{track}`
- **Source**: ID3 tag TRCK
- **Format**: Zero-padded (e.g., "01", "12")
- **Empty if**: Not in tags

---

## Migration from Old Template System

### Old Variables (Removed)

| Old Variable | Replacement | Notes |
|--------------|-------------|-------|
| `{mix_paren}` | `({mix})` | Add parens yourself for clarity |
| `{kb}` | `[{camelot} {bpm}]` | Add brackets yourself for clarity |

### Old Default Template
```
{artist} - {title}{mix_paren}{kb}
```

### New Default Template
```
{artist} - {title} [{camelot} {bpm}]
```

**Why changed:**
- More explicit about formatting
- Easier to understand what output looks like
- Follows best practices (atomic variables)
- User controls all formatting

---

## Best Practices

### ✅ DO
- Use descriptive variable names
- Add explicit formatting (spaces, brackets, parens)
- Test template with Preview before Rename
- Include BPM and key for DJ workflow
- Use Camelot for harmonic mixing

### ❌ DON'T
- Use variables you don't understand
- Rely on implicit spacing
- Skip Preview step
- Use special characters that are illegal in filenames: `/ \ : * ? " < > |`

---

## Testing Your Template

1. Enter your template in the TUI
2. Click **Preview (P)**
3. Check the "New Name" column in results
4. Verify formatting looks correct
5. Adjust template if needed
6. Preview again to confirm
7. Click **Rename Files (R)** when satisfied

---

## Common Patterns

### DJ Library Standard
```
{artist} - {title} [{camelot} {bpm}]
```

### Rekordbox Compatible
```
{track} {artist} - {title} [{key} {bpm}]
```

### Traktor Compatible
```
{artist} - {title} {bpm}
```

### Serato Compatible
```
{artist} - {title} ({year}) [{camelot} {bpm}]
```

---

## Questions?

See `README.md` for more examples and usage instructions.
