# Remember Last Directory - Best Practices

**Date**: 2026-01-30
**Research Topic**: Should file browser remember last directory? What's the fallback strategy?
**Answer**: YES - This is standard UX that users expect

---

## Research Question

User asked: *"Should the file browser save where it last was (the last subfolder it was in... save it with the other config save info) so that if a user stops the web server and restarts it, they can continue from the same area? Is that a best practice?"*

**Short Answer**: **YES** - This is standard UX behavior that users expect.

---

## Research Findings

### 1. Is This a Best Practice?

**YES** ✅ - Industry standard across all major applications

**Evidence**:
- SaveFileDialog on Windows/Mac automatically remembers last folder opened
- Firefox remembers last download folder on a per-site basis
- Most professional applications implement this behavior
- Users find it frustrating when browsers DON'T remember the previously selected folder

**User Expectations**:
- Users expect file browsers to remember last location when reopening
- Especially important for repetitive workflows (like batch renaming music files)
- Matching standard browser behavior helps avoid confusing users

**Sources**:
- [File Browser Remember Last Location Feature Request](https://github.com/marvinkreis/rofi-file-browser-extended/issues/26)
- [Firefox Download Folder Memory](https://support.mozilla.org/mk/questions/1386344)
- [UX Design Choices for File Managers](https://techtipsharing.medium.com/design-choices-of-ux-using-file-manager-as-example-6e18d1b2b9fc)
- [Chrome Save Last Download Path](https://support.google.com/chrome/thread/28782912/how-to-make-the-browser-save-the-last-download-path)

---

### 2. Fallback Strategy (When Directory No Longer Exists)

**Question**: *"If the directory they were last in no longer exists, then what's the best practice: default to ~/home, or default to /, or default to the parent directory, and if that doesn't exist, keep going up until a directory exists?"*

**Best Practice**: **Walk up to parent directories, fallback to home (~)**

**Recommended Fallback Order**:
```
1. Try saved directory path
2. If not exists → Try parent directory
3. If parent not exists → Keep walking up parent chain
4. If reach root (/) → Fallback to home directory (~)
5. NEVER default to / (root) - bad UX
```

**Why This Approach?**

| Strategy | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Parent directory walk-up** | Most likely to find related location, maintains context | Requires loop logic | ✅ **Best** |
| **Home directory (~)** | Always exists, user has permissions, relevant for music files | Loses all context | ✅ **Good fallback** |
| **Root directory (/)** | Always exists | Users can't write here, overwhelming for music apps | ❌ **Never use** |
| **Documents folder** | Often contains music | May not exist on all systems | 🟡 **Alternative** |

**Implementation Logic**:
```python
import os
from pathlib import Path

def get_initial_directory(saved_path: str) -> str:
    """
    Get initial directory with intelligent fallback.

    Strategy:
    1. Try saved path
    2. Walk up parent directories until valid dir found
    3. Fallback to home directory if nothing found

    Args:
        saved_path: Last saved directory path

    Returns:
        Valid directory path that exists
    """
    # Try saved path directly
    if saved_path and os.path.exists(saved_path) and os.path.isdir(saved_path):
        return saved_path

    # Walk up parent directories
    if saved_path:
        current = Path(saved_path)

        # Keep going up until we find a valid directory or reach root
        while current != current.parent:  # Not at root
            parent = current.parent
            if parent.exists() and parent.is_dir():
                return str(parent)
            current = parent

    # Ultimate fallback: home directory
    return os.path.expanduser("~")
```

**Sources**:
- [File Picker Initial Directory Fallback](https://github.com/flet-dev/flet/issues/5829)
- [Save File with Picker - Microsoft UWP](https://learn.microsoft.com/en-us/windows/uwp/files/quickstart-save-a-file-with-a-picker)
- [Remember Last Used Folder PR](https://github.com/ksnip/ksnip/pull/264)

---

### 3. Configuration Options

**Best Practice**: Make it configurable (but enabled by default)

**Config Schema**:
```json
{
  "last_directory": "/Users/username/Music/Albums/Electronic",
  "remember_last_directory": true
}
```

**Why Configurable?**
- Some users may prefer always starting from home
- Privacy concerns (multi-user systems)
- Flexibility for different workflows

**Default**: **Enabled** (most users expect this behavior)

**Sources**:
- [Configurable Remember Folder Behavior](https://github.com/marvinkreis/rofi-file-browser-extended/issues/26)
- [Per-Context Directory Memory](https://support.mozilla.org/mk/questions/1386344)

---

## Implementation Recommendations

### Backend Changes

**1. Update config.py**
```python
# crate/core/config.py
DEFAULT_CONFIG = {
    # ... existing config ...
    "last_directory": "",  # Empty string = use home directory
    "remember_last_directory": True,  # Enable by default
}
```

**2. Add helper function**
```python
# crate/core/config.py
def get_initial_directory() -> str:
    """Get initial directory with fallback logic."""
    config = load_config()

    if not config.get("remember_last_directory", True):
        return os.path.expanduser("~")

    saved_path = config.get("last_directory", "")
    return get_valid_directory(saved_path)

def get_valid_directory(saved_path: str) -> str:
    """Walk up parents to find valid directory."""
    # Implementation as shown above
    pass
```

### Frontend Changes

**1. Save directory when user browses**
```javascript
// app.js - in directory browse handler
async browseDirectory() {
    const path = await this.api.selectDirectory();

    // Save to config
    await this.api.updateConfig({
        last_directory: path
    });

    await this.loadDirectory(path);
}
```

**2. Auto-load last directory on startup**
```javascript
// app.js - in init()
async init() {
    // ... existing init ...

    // Auto-load last directory if enabled
    const config = await this.api.getConfig();
    if (config.remember_last_directory && config.last_directory) {
        const validPath = await this.api.getInitialDirectory();
        if (validPath) {
            await this.loadDirectory(validPath);
        }
    }
}
```

---

## Benefits

### User Experience
- ✅ Saves time for repetitive workflows
- ✅ Maintains context between sessions
- ✅ Matches user expectations (industry standard)
- ✅ Better for DJ workflow (organize albums in batches over multiple sessions)

### Technical
- ✅ Simple implementation (1-2 hours)
- ✅ Low risk (config-based, can be disabled)
- ✅ No breaking changes
- ✅ Leverages existing config system

---

## Testing Checklist

### Test Case 1: Normal Flow
- [ ] Browse to directory `/Users/test/Music/Albums`
- [ ] Restart server
- [ ] **Expected**: Auto-loads `/Users/test/Music/Albums`

### Test Case 2: Directory Deleted
- [ ] Browse to `/Users/test/Music/Albums/Electronic`
- [ ] Delete `/Users/test/Music/Albums/Electronic`
- [ ] Restart server
- [ ] **Expected**: Loads parent `/Users/test/Music/Albums`

### Test Case 3: Entire Parent Chain Deleted
- [ ] Browse to `/Users/test/Music/Albums/Electronic`
- [ ] Delete entire `/Users/test/Music` directory
- [ ] Restart server
- [ ] **Expected**: Loads home directory `~`

### Test Case 4: Feature Disabled
- [ ] Set `remember_last_directory: false` in config
- [ ] Browse to `/Users/test/Music`
- [ ] Restart server
- [ ] **Expected**: Loads home directory (doesn't remember last)

### Test Case 5: Empty Config (First Run)
- [ ] Delete config file
- [ ] Start server
- [ ] **Expected**: Loads home directory

---

## Privacy Considerations

**Multi-User Systems**: Last directory path stored in config could reveal user activity.

**Mitigation**:
- Config file has secure permissions (0o600)
- Only accessible to user who runs the server
- Can be disabled via config flag

**Not a Concern**: Single-user desktop application context.

---

## Comparison with Other Applications

| Application | Behavior | Fallback |
|-------------|----------|----------|
| **Windows Explorer** | Remembers last location per session | N/A (always exists) |
| **macOS Finder** | Remembers last location | N/A (always exists) |
| **Firefox Downloads** | Remembers per-site | Default download folder |
| **Chrome Downloads** | Remembers last used | Default download folder |
| **VS Code File Open** | Remembers last workspace | Home directory |
| **Audacity** | Remembers last import/export location | Home directory |
| **iTunes/Music** | Always uses Music library location | Music folder |

**Conclusion**: Our approach aligns with industry standards.

---

## Related Features (Future Enhancements)

### Per-Directory Templates
- Save template preferences per directory
- Example: Electronic music folder uses different template than Jazz folder

### Directory Bookmarks
- Allow users to bookmark frequently used directories
- Quick access dropdown in file browser

### Recent Directories
- Show list of recently browsed directories
- Quick switch between recent locations

**Priority**: Low (implement basic "remember last" first)

---

## Sources

### User Expectations
- [File Browser Remember Last Location](https://github.com/marvinkreis/rofi-file-browser-extended/issues/26)
- [Firefox Download Folder Memory](https://support.mozilla.org/mk/questions/1386344)
- [Linux Mint Browser Directory Memory](https://forums.linuxmint.com/viewtopic.php?t=143520)
- [Chrome Save Last Path](https://support.google.com/chrome/thread/28782912/how-to-make-the-browser-save-the-last-download-path)

### UX Design
- [File Manager UX Design Choices](https://techtipsharing.medium.com/design-choices-of-ux-using-file-manager-as-example-6e18d1b2b9fc)

### Fallback Strategy
- [File Picker Initial Directory](https://github.com/flet-dev/flet/issues/5829)
- [Microsoft UWP File Picker](https://learn.microsoft.com/en-us/windows/uwp/files/quickstart-save-a-file-with-a-picker)
- [Freeplane Default Folder Discussion](https://sourceforge.net/p/freeplane/discussion/758437/thread/3d09b610af/)

### Implementation Examples
- [Remember Last Folder PR](https://github.com/ksnip/ksnip/pull/264)
- [File Picker Discussion](https://github.com/zauberzeug/nicegui/discussions/283)

---

**Research Complete**: 2026-01-30
**Recommendation**: ✅ IMPLEMENT - Standard UX feature with high user value
**Effort**: Low (1-2 hours)
**Impact**: Medium (quality of life improvement)
