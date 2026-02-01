# Design: Low-Friction Automation for Massive Libraries

**Task**: #118
**Date**: 2026-01-31
**Status**: In Progress
**Priority**: HIGH

---

## Problem Statement

Current UX has significant friction for users with massive libraries (50K+ songs):

1. **Long Metadata Loading** - No progress feedback, appears frozen
2. **Manual Per-Album Selection** - Must click checkboxes for each album (tedious for 100+ albums)
3. **No Conflict Resolution UI** - User can't choose between MusicBrainz vs AI vs ID3
4. **Preview Not Persistent** - Template changes reset on page refresh
5. **No Automation** - User must babysit app for hours during large operations

**User Feedback**:
> "Keep thinking low friction for user. High quality UX and UI. Users want automation and can't spend hours baby sitting the app."

---

## Design Principles

1. **Zero-Click Where Possible** - Auto-detect, auto-select, auto-apply
2. **Progress Transparency** - Always show what's happening and ETA
3. **Interruptible** - User can pause, cancel, resume anytime
4. **Smart Defaults** - 80% of users should need 0-1 clicks
5. **Power User Escapes** - Advanced options available but not required

---

## Solution Architecture

### 1. Intelligent Auto-Pilot Mode

**Feature**: One-click rename for entire library with smart detection

```javascript
// Auto-pilot workflow
class AutoPilot {
    async execute(directory) {
        // Step 1: Analyze directory structure
        const analysis = await this.analyzeDirectory(directory);

        // Step 2: Auto-select smart detections
        const autoSelections = this.autoSelect(analysis);

        // Step 3: Generate preview
        const preview = await this.generatePreview(autoSelections);

        // Step 4: Show confirmation with one-click approval
        const approved = await this.showSmartConfirmation(preview);

        if (approved) {
            // Step 5: Execute rename in background
            await this.executeRename(autoSelections);
        }
    }

    autoSelect(analysis) {
        /**
         * Auto-select albums based on confidence:
         * - ALBUM (high confidence) → Use smart template
         * - PARTIAL_ALBUM (medium) → Use smart template
         * - INCOMPLETE_ALBUM (low) → Use global template
         * - SINGLES → Use global template
         */
        return analysis.albums.filter(album =>
            album.detection.confidence === 'high' ||
            album.detection.confidence === 'medium'
        );
    }

    async showSmartConfirmation(preview) {
        /**
         * Show summary instead of full file list:
         * - "10 albums will use smart track templates"
         * - "5 albums will use your global template"
         * - "Total: 2,547 files will be renamed"
         * - [Preview Sample] [Approve & Rename] [Cancel]
         */
        return await UI.showSmartConfirmationDialog(preview);
    }
}
```

**UI Design**:
```
┌─────────────────────────────────────────────┐
│ 🎯 Smart Rename Ready                       │
├─────────────────────────────────────────────┤
│                                             │
│ ✓ 10 albums detected with track sequences  │
│   → Will use: "{track} - {artist} - {title}│
│                                             │
│ ℹ 5 albums without track sequences          │
│   → Will use: "{artist} - {title} [{bpm}]" │
│                                             │
│ 📊 Total: 2,547 files will be renamed       │
│                                             │
│ [Show Sample Preview ▼] [Rename All] [✕]   │
└─────────────────────────────────────────────┘
```

**Benefits**:
- 1-click approval instead of selecting 100+ album checkboxes
- Clear summary of what will happen
- Sample preview available but not required
- Users can review or trust auto-detection

### 2. Progress Dashboard with ETA

**Feature**: Real-time progress with estimated time remaining

```javascript
class ProgressDashboard {
    constructor() {
        this.startTime = null;
        this.processed = 0;
        this.total = 0;
        this.currentPhase = 'idle';
        this.errors = [];
    }

    update(event) {
        this.processed = event.processed;
        this.total = event.total;
        this.currentPhase = event.phase;

        // Calculate ETA
        const elapsed = Date.now() - this.startTime;
        const rate = this.processed / (elapsed / 1000);  // files per second
        const remaining = this.total - this.processed;
        const eta = remaining / rate;  // seconds

        this.render();
    }

    render() {
        // Show multi-phase progress:
        // Phase 1: Loading metadata (25% weight)
        // Phase 2: Analyzing context (10% weight)
        // Phase 3: Generating previews (15% weight)
        // Phase 4: Renaming files (50% weight)

        const totalProgress = this.calculateWeightedProgress();
        const etaFormatted = this.formatDuration(this.eta);

        UI.updateProgressBar(totalProgress, etaFormatted);
        UI.updateCurrentFile(event.currentFile);
        UI.updatePhaseIndicator(this.currentPhase);
    }

    formatDuration(seconds) {
        if (seconds < 60) return `${Math.round(seconds)}s`;
        if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
        return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
    }
}
```

**UI Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ 🔄 Renaming Files                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Phase 4 of 4: Renaming files                                │
│ ████████████████████████████████████░░░░░░░░ 78% (1,987/2,547│
│                                                             │
│ Current: 03 - The Beatles - Hey Jude.mp3                    │
│ Speed: 12 files/sec                                          │
│ Estimated time remaining: 45 seconds                         │
│                                                             │
│ ✓ 1,985 renamed  ⚠ 2 warnings  ✗ 0 errors                  │
│                                                             │
│ [Pause] [Cancel] [View Log]                                │
└─────────────────────────────────────────────────────────────┘
```

**Benefits**:
- User knows exactly what's happening
- ETA reduces anxiety ("how long will this take?")
- Can see errors in real-time
- Pause/cancel available anytime

### 3. Metadata Conflict Resolution UI

**Feature**: User chooses priority when sources disagree

```javascript
class ConflictResolver {
    async resolveConflicts(conflicts) {
        /**
         * Show conflicts grouped by field:
         * - BPM: 45 files have conflicting BPM values
         * - Key: 12 files have conflicting key values
         *
         * Let user choose resolution strategy:
         * - Trust ID3 tags (current metadata)
         * - Trust MusicBrainz (network lookup)
         * - Trust AI Audio Analysis (detected)
         * - Review each conflict manually (advanced)
         */

        const resolution = await UI.showConflictResolutionDialog(conflicts);

        return resolution;  // { bpm: 'ai_audio', key: 'musicbrainz', ... }
    }
}
```

**UI Design**:
```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Metadata Conflicts Detected                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 45 files have conflicting BPM values                    │
│ 12 files have conflicting key values                    │
│                                                         │
│ Choose resolution strategy:                             │
│                                                         │
│ ○ Trust existing ID3 tags (fastest, no network)        │
│ ○ Trust MusicBrainz (most accurate, requires network)  │
│ ● Trust AI Audio Analysis (recommended, balanced)      │
│ ○ Review each conflict manually (advanced users)       │
│                                                         │
│ [Apply] [Cancel]                                        │
└─────────────────────────────────────────────────────────┘
```

**Benefits**:
- User has control over conflict resolution
- Can choose speed vs accuracy trade-off
- One choice applies to all conflicts (low friction)
- Advanced users can review individually

### 4. Template Persistence

**Feature**: Remember user's template choices

```javascript
class TemplatePersistence {
    async saveTemplateChoice(directory, template, perAlbumSelections) {
        /**
         * Save to local storage or backend:
         * - Template used
         * - Per-album selections
         * - Timestamp
         *
         * Next time user loads same directory:
         * - Auto-apply same template
         * - Auto-select same albums
         * - Show "Using saved preferences" notification
         */

        const preferences = {
            directory: directory,
            template: template,
            perAlbumSelections: perAlbumSelections,
            timestamp: Date.now()
        };

        await localStorage.setItem(`template_pref_${directory}`, JSON.stringify(preferences));
    }

    async loadTemplateChoice(directory) {
        const saved = await localStorage.getItem(`template_pref_${directory}`);

        if (saved) {
            const preferences = JSON.parse(saved);

            // Check if not too old (7 days)
            const age = Date.now() - preferences.timestamp;
            if (age < 7 * 24 * 60 * 60 * 1000) {
                return preferences;
            }
        }

        return null;
    }
}
```

**UI Notification**:
```
┌─────────────────────────────────────────────┐
│ ℹ Using saved template preferences           │
│ Last used 2 days ago                         │
│ [Keep] [Change]                              │
└─────────────────────────────────────────────┘
```

**Benefits**:
- User doesn't re-enter template every time
- Per-album selections restored
- Can override if needed

### 5. Background Processing with Notifications

**Feature**: Process in background, notify when done

```javascript
class BackgroundProcessor {
    async startBackgroundRename(request) {
        /**
         * Start rename operation in background:
         * - User can close browser tab
         * - Operation continues on server
         * - Browser notification when complete
         * - Email notification (optional)
         */

        const operationId = await api.startBackgroundRename(request);

        // Request notification permission
        if (Notification.permission === 'default') {
            await Notification.requestPermission();
        }

        // Close current tab notification
        UI.showNotification('Operation started in background. You can close this tab.');

        // Poll for completion
        const poller = setInterval(async () => {
            const status = await api.getOperationStatus(operationId);

            if (status.status === 'completed') {
                clearInterval(poller);

                // Show browser notification
                new Notification('Crate - Rename Complete', {
                    body: `Successfully renamed ${status.results.renamed} files`,
                    icon: '/static/icon.png'
                });

                // Optional: Send email
                if (user.emailNotifications) {
                    await api.sendEmailNotification(operationId);
                }
            }
        }, 10000);  // Check every 10 seconds
    }
}
```

**Benefits**:
- User doesn't need to keep browser open
- Can work on other tasks while processing
- Notified when complete
- No babysitting required

### 6. Smart Batch Scheduling

**Feature**: Auto-schedule batches during low-activity hours

```python
class SmartScheduler:
    def schedule_batch_processing(self, files, user_preferences):
        """
        Intelligently schedule batch processing:
        - Detect system idle time (low CPU, no user activity)
        - Schedule heavy operations (audio analysis) during idle
        - Process lightweight operations (rename) immediately
        - Respect user's "active hours" preferences
        """

        if len(files) < 1000:
            # Small batch - process immediately
            return self.process_immediately(files)

        # Large batch - check if we should schedule
        if self.is_system_idle() and not self.is_active_hours(user_preferences):
            # Process now (system idle, not during active hours)
            return self.process_immediately(files)
        else:
            # Schedule for later
            scheduled_time = self.find_next_idle_window(user_preferences)
            return self.schedule_for_later(files, scheduled_time)

    def is_system_idle(self):
        """Check if system is idle (low CPU, no mouse/keyboard)."""
        return psutil.cpu_percent(interval=1) < 20

    def is_active_hours(self, user_preferences):
        """Check if current time is during user's active hours."""
        current_hour = datetime.now().hour
        active_start = user_preferences.get('active_hours_start', 9)
        active_end = user_preferences.get('active_hours_end', 22)

        return active_start <= current_hour < active_end
```

**UI Design**:
```
┌─────────────────────────────────────────────────────────┐
│ 📅 Smart Scheduling                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ This operation will take ~3 hours                       │
│                                                         │
│ ● Process now (system currently idle)                  │
│ ○ Schedule for tonight (10:00 PM - 2:00 AM)           │
│ ○ Schedule for weekend (Saturday 8:00 AM)              │
│                                                         │
│ ☐ Send email notification when complete                │
│                                                         │
│ [Start] [Cancel]                                        │
└─────────────────────────────────────────────────────────┘
```

**Benefits**:
- Heavy operations run when system idle
- User doesn't experience slowdowns
- Can schedule for overnight processing
- Truly hands-off automation

### 7. Quick Actions & Keyboard Shortcuts

**Feature**: Power user shortcuts for common workflows

```javascript
class QuickActions {
    registerShortcuts() {
        // Cmd/Ctrl + Enter - Execute with smart defaults
        keyboard.register('mod+enter', () => {
            this.executeWithSmartDefaults();
        });

        // Cmd/Ctrl + Shift + R - Retry failed files
        keyboard.register('mod+shift+r', () => {
            this.retryFailedFiles();
        });

        // Cmd/Ctrl + D - Toggle audio detection
        keyboard.register('mod+d', () => {
            this.toggleAudioDetection();
        });

        // Cmd/Ctrl + Shift + A - Auto-select all albums
        keyboard.register('mod+shift+a', () => {
            this.autoSelectAllAlbums();
        });
    }

    async executeWithSmartDefaults() {
        /**
         * One-key execution:
         * - Use smart detection
         * - Auto-select high-confidence albums
         * - Use default conflict resolution
         * - Start rename immediately
         */
        await AutoPilot.execute(this.currentDirectory);
    }
}
```

**UI Shortcuts Help**:
```
┌─────────────────────────────────────────────┐
│ ⌨️ Keyboard Shortcuts                        │
├─────────────────────────────────────────────┤
│ Cmd+Enter    Execute with smart defaults   │
│ Cmd+D        Toggle audio detection        │
│ Cmd+Shift+A  Auto-select all albums        │
│ Cmd+Shift+R  Retry failed files            │
│ ?            Show this help                │
└─────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Auto-Pilot Mode (Week 1)
1. Implement auto-selection logic
2. Create smart confirmation dialog
3. Add one-click approval workflow
4. Test with 50K library

### Phase 2: Progress Dashboard (Week 1)
1. Implement weighted progress calculation
2. Add ETA calculation
3. Create multi-phase progress UI
4. Add pause/cancel/resume

### Phase 3: Conflict Resolution UI (Week 2)
1. Detect metadata conflicts
2. Create resolution dialog
3. Apply resolution strategy
4. Test with conflicting sources

### Phase 4: Persistence & Background (Week 2)
1. Implement template persistence
2. Add background processing
3. Add browser notifications
4. Add email notifications (optional)

### Phase 5: Smart Scheduling (Week 3)
1. Implement idle detection
2. Add scheduling UI
3. Add active hours preferences
4. Test overnight processing

### Phase 6: Quick Actions (Week 3)
1. Register keyboard shortcuts
2. Create shortcuts help dialog
3. Add quick action buttons
4. User acceptance testing

---

## Success Metrics

1. **Time to First Rename**: < 10 seconds (from directory load to rename start)
2. **User Clicks Required**: 1-3 clicks for 80% of use cases
3. **Background Processing Adoption**: 50%+ of large operations
4. **User Satisfaction**: 4.5/5 stars on "ease of use"

---

## Status

✅ **Design Complete**
⏳ **Implementation**: Ready to start
📋 **Next Steps**: Implement Phase 1 (auto-pilot mode)

**Estimated Implementation Time**: 3 weeks
**Testing Time**: 1 week
**Total**: 4 weeks to production

---

**Task #118 Status**: Design complete, ready for implementation approval
