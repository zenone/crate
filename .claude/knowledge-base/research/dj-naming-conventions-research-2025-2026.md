# DJ Music Library Naming Conventions - 2025-2026 Research

**Research Date:** 2026-01-29
**Purpose:** Document industry best practices for DJ filename naming and metadata management

## Executive Summary

Modern DJ software (Rekordbox, Serato, Traktor) differs significantly in how they handle metadata:
- **Rekordbox**: Stores metadata in internal database (not in files)
- **Serato**: Embeds all metadata into audio files (proprietary GEOB tags)
- **Traktor**: Hybrid approach with some data in files, some in database

**Key Insight:** For maximum portability and backup safety, **filenames should include essential DJ metadata** (BPM, Key/Camelot) since not all software writes to ID3 tags, and database corruption can lose cue points/loops.

---

## 1. Recommended Filename Formats

### Format A: Artist - Title [Key BPM]
```
Deadmau5 - Strobe [8A 128].mp3
Calvin Harris - Summer [12B 128].mp3
```
**Best for:** Club DJs, organized libraries, quick visual scanning

### Format B: BPM Key - Artist - Title
```
128 8A - Deadmau5 - Strobe.mp3
128 12B - Calvin Harris - Summer.mp3
```
**Best for:** BPM-focused mixing, energy-level organization

### Format C: Artist - Title (Mix) [Key BPM]
```
Deadmau5 - Strobe (Original Mix) [8A 128].mp3
Deadmau5 - Strobe (Club Edit) [8A 130].mp3
```
**Best for:** Tracks with multiple versions/remixes

---

## 2. Essential Metadata Fields

### Priority 1 (Critical for DJing)
| Field | Purpose | Example |
|-------|---------|---------|
| `{artist}` | Track identification | Deadmau5 |
| `{title}` | Track identification | Strobe |
| `{bpm}` | Tempo matching | 128 |
| `{key}` | Harmonic mixing | A minor |
| `{camelot}` | Harmonic mixing (DJ notation) | 8A |

### Priority 2 (Important for Organization)
| Field | Purpose | Example |
|-------|---------|---------|
| `{genre}` | Style categorization | Progressive House |
| `{year}` | Era/era-specific sets | 2009 |
| `{label}` | Record label tracking | Ultra Records |
| `{mix}` | Version differentiation | Original Mix, Radio Edit |

### Priority 3 (Nice to Have)
| Field | Purpose | Example |
|-------|---------|---------|
| `{album}` | Release tracking | For Lack Of A Better Name |
| `{track}` | Album order | 04 |
| `{catalog}` | Label catalog number | ULTRA001 |

---

## 3. Camelot Wheel System

The **Camelot Wheel** is the industry standard for harmonic mixing in 2025-2026:

### Key Notation Conversion
| Musical Key | Camelot | Musical Key | Camelot |
|-------------|---------|-------------|---------|
| C major | 8B | A minor | 8A |
| G major | 9B | E minor | 9A |
| D major | 10B | B minor | 10A |
| A major | 11B | F# minor | 11A |
| E major | 12B | C# minor | 12A |
| B major | 1B | G# minor | 1A |
| F# major | 2B | D# minor | 2A |
| Db major | 3B | Bb minor | 3A |
| Ab major | 4B | F minor | 4A |
| Eb major | 5B | C minor | 5A |
| Bb major | 6B | G minor | 6A |
| F major | 7B | D minor | 7A |

### Harmonic Mixing Rules
- **Same number**: Perfect match (8A → 8A, 8B → 8B)
- **±1 number**: Smooth transition (8A → 9A or 7A)
- **Letter swap**: Major/minor swap (8A → 8B)
- **Energy boost**: +7 on wheel (8A → 3A)

**Tools:** Mixed In Key, Rekordbox, Serato all detect and label keys in Camelot notation automatically.

---

## 4. Software-Specific Practices

### Rekordbox (Pioneer DJ)
- **Metadata Storage:** Internal database only (no file embedding)
- **Export Requirement:** Must export library to retain beatgrids, cue points, loops
- **Portability:** Poor - database corruption loses all DJ prep work
- **Filename Strategy:** **CRITICAL** - Include BPM/Key in filename as backup
- **ID3 Tags:** Basic tags only (artist, title, album, genre)

### Serato
- **Metadata Storage:** Embedded in audio files (proprietary GEOB tags)
- **Portability:** Excellent - files carry all cues, loops, waveforms
- **Filename Strategy:** Optional - metadata survives in file
- **Compatibility:** GEOB tags not readable by other software
- **ID3 Tags:** Full support + proprietary extensions

### Traktor (Native Instruments)
- **Metadata Storage:** Hybrid - some in files, some in database
- **Waveform Data:** Embedded in MP3, AIFF, FLAC, WAV
- **Portability:** Good for waveforms/art, limited for cue points
- **Filename Strategy:** Recommended for full portability
- **ID3 Tags:** Standard support with cover art embedding

---

## 5. Use Case Recommendations

### Club/Venue DJs
**Format:** `Artist - Title [Camelot BPM].mp3`
- Quick visual scanning in booth
- Backup-friendly (no database dependency)
- Works across all software/hardware
- Example: `Deadmau5 - Strobe [8A 128].mp3`

### Mobile/Wedding DJs
**Format:** `BPM - Artist - Title.mp3` or `Genre - Artist - Title.mp3`
- BPM sorting for energy control
- Genre-first for client requests
- Less focus on harmonic mixing
- Example: `128 - Calvin Harris - Summer.mp3`

### Producer/Studio DJs
**Format:** `Artist - Title (Mix).mp3`
- Focus on track versions
- Less critical for BPM/key (in DAW)
- Example: `Deadmau5 - Strobe (Original Mix).mp3`

### Record Pool Users
**Format:** Use pool's naming + add metadata
- Pools provide robust metadata
- Add personal BPM/key tags to filename
- Maintain original naming for updates
- Example: `[POOL] Artist - Title [8A 128].mp3`

---

## 6. Metadata vs. Filename Trade-offs

### Store in ID3 Tags (Always)
✅ Artist, Title, Album, Year, Genre
✅ BPM (standard TBPM frame)
✅ Key (standard TKEY frame)
✅ Label (TPUB frame)
✅ Comments, Ratings

**Why:** Universal compatibility, searchable in all software

### Store in Filename (Recommended)
✅ BPM
✅ Key/Camelot
✅ Mix version (if multiple versions)

**Why:**
- Instant visual identification
- Survives database corruption
- Works on non-DJ equipment (car stereos, CDJs without Rekordbox link)
- USB backup portability

### Never Store in Filename
❌ Genre (use ID3)
❌ Album (use ID3)
❌ Year (use ID3)
❌ Label (use ID3)

**Why:** Makes filenames too long, harder to read, not sortable

---

## 7. Common Pitfalls to Avoid

### ❌ Bad Practices
```
track1.mp3                           # No metadata
Calvin.Harris.-.Summer.mp3           # Hard to read
Calvin_Harris_-_Summer_128bpm.mp3    # Underscores, verbose
CALVIN HARRIS - SUMMER.MP3           # ALL CAPS
Calvin Harris - Summer (128 BPM) (A Minor) (2014) (Columbia Records).mp3  # TOO LONG
```

### ✅ Good Practices
```
Calvin Harris - Summer [12B 128].mp3           # Clean, scannable
Calvin Harris - Summer (Radio Edit) [12B 128].mp3  # Includes version
128 12B - Calvin Harris - Summer.mp3          # BPM-first sorting
```

---

## 8. Recommended Default Templates

### General Electronic/House
```
{artist} - {title} [{camelot} {bpm}]
```
**Output:** `Deadmau5 - Strobe [8A 128].mp3`

### With Mix Version
```
{artist} - {title} ({mix}) [{camelot} {bpm}]
```
**Output:** `Deadmau5 - Strobe (Original Mix) [8A 128].mp3`

### BPM-First (Energy Sorting)
```
{bpm} {camelot} - {artist} - {title}
```
**Output:** `128 8A - Deadmau5 - Strobe.mp3`

### Label/Catalog (Record Collectors)
```
{artist} - {title} [{label} {catalog}]
```
**Output:** `Deadmau5 - Strobe [Ultra Records ULTRA001].mp3`

### Minimal (Let Software Handle It)
```
{artist} - {title}
```
**Output:** `Deadmau5 - Strobe.mp3`
**Note:** Only use if you trust your DJ software's database

---

## 9. 2025-2026 Trends

### Emerging Practices
- **Stem Separation:** DJs now storing stem files (vocals, drums, bass, melody) with similar naming
- **AI Key Detection:** Tools like Mixed In Key 10+, LANDR improving accuracy to 98%+
- **Energy Level Tags:** Numeric 1-10 scale for set building
- **Phrase Markers:** Rekordbox 6+ auto-detects intro/verse/chorus/outro
- **Streaming Integration:** Less focus on file management as Beatport LINK/Tidal grow

### Software Evolution
- **Rekordbox 7:** Still doesn't embed metadata in files (philosophical choice)
- **Serato DJ Pro 3.x:** Continues file-embedding approach
- **Traktor Pro 4:** Improved stem support, still hybrid storage

---

## 10. Implementation Recommendations for DJ MP3 Renamer

### Default Template
```
{artist} - {title} [{camelot} {bpm}]
```

### Preset Templates to Include
1. **Electronic/House:** `{artist} - {title} [{camelot} {bpm}]`
2. **With Mix:** `{artist} - {title} ({mix}) [{camelot} {bpm}]`
3. **BPM First:** `{bpm} {camelot} - {artist} - {title}`
4. **Key Only:** `{artist} - {title} [{key}]`
5. **BPM Only:** `{artist} - {title} [{bpm}]`
6. **Minimal:** `{artist} - {title}`
7. **Full Metadata:** `{artist} - {title} ({year}) [{camelot} {bpm}]`

### Variable Priority
**Essential:** artist, title, bpm, key, camelot
**Important:** mix, genre, year, label
**Optional:** album, track, catalog

---

## Sources

- [How To Create The Ultimate DJ Music Library In 2026 (Step-By-Step) | ZIPDJ](https://www.zipdj.com/blog/dj-music-library)
- [DJ Software Secrets: Where Your Info Really Lives - Digital DJ Tips](https://www.digitaldjtips.com/dj-software-secrets/)
- [An Essential Guide To Organising Your Music Library - Digital DJ Tips](https://www.digitaldjtips.com/music-library-organisation-part-4/)
- [The DJ's Guide to the Camelot Wheel and Harmonic Mixing | DJ.Studio](https://dj.studio/blog/camelot-wheel)
- [The Camelot Wheel Explained (2025 Guide) | How DJs Mix in Key](https://musiccitysf.com/accelerator-blog/camelot-wheel-dj-mixing-guide/)
- [Good File Naming and Metadata Practices for Your Audio Tracks](https://shierozow.com/good-file-naming-and-metadata-practices-for-your-audio-tracks/)
- [Rekordbox tagging (ID3) and database questions – Pioneer DJ](https://forums.pioneerdj.com/hc/en-us/community/posts/203052319-Rekordbox-tagging-ID3-and-database-questions)
- [Storing metadata externally? | Serato.com](https://serato.com/forum/discussion/1504872)

---

**Conclusion:** For maximum portability and data safety in 2025-2026, DJs should include BPM and Camelot key in filenames, regardless of which software they use. This protects against database corruption and ensures compatibility across all platforms.
