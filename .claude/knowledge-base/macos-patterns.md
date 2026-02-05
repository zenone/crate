# macOS Development Patterns

Patterns specific to macOS application development.

---

## launchd Over Cron

**Pattern**: Always use launchd instead of cron for scheduled tasks on macOS.

**Why**:
- Cron runs in restricted sandbox (can't access Dropbox, iCloud, user directories)
- launchd integrates with macOS power management (won't run on battery if configured)
- launchd survives reboots automatically
- Better logging and error handling

**Basic launchd plist** (`~/Library/LaunchAgents/com.example.task.plist`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.example.task</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/my-script.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer><!-- Every 5 minutes -->
    <key>StandardOutPath</key>
    <string>/tmp/my-script.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/my-script.stderr.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

**Management**:
```bash
# Load (enable)
launchctl load ~/Library/LaunchAgents/com.example.task.plist

# Unload (disable)
launchctl unload ~/Library/LaunchAgents/com.example.task.plist

# Check status
launchctl list | grep example

# Run now (for testing)
launchctl start com.example.task
```

**Locations**:
- `~/Library/LaunchAgents/` - User agents (run as user)
- `/Library/LaunchAgents/` - Global agents (run as user, for all users)
- `/Library/LaunchDaemons/` - Daemons (run as root)

---

## iCloud/Dropbox Safe Operations

**Problem**: Files in cloud-synced directories can be evicted (not downloaded) or locked during sync.

**Safe Patterns**:
```python
from pathlib import Path

def is_file_available(path: Path) -> bool:
    """Check if iCloud/Dropbox file is actually downloaded."""
    # iCloud files have extended attribute when evicted
    import subprocess
    result = subprocess.run(
        ['xattr', '-p', 'com.apple.icloud.itemdownloadstatus', str(path)],
        capture_output=True
    )
    if result.returncode == 0:
        return b'downloaded' in result.stdout
    return path.exists()  # Not an iCloud file, use normal check

def wait_for_sync(path: Path, timeout: int = 30) -> bool:
    """Wait for cloud sync to complete."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            # Try to get exclusive lock
            with open(path, 'r') as f:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return True
        except (IOError, OSError):
            time.sleep(0.5)
    return False
```

**Directory Exclusion**:
```bash
# Exclude directory from Dropbox sync
xattr -w com.dropbox.ignored 1 /path/to/dir

# Exclude from iCloud (add .nosync suffix)
mv .venv .venv.nosync
ln -s .venv.nosync .venv
```

---

## TCC Permissions (Transparency, Consent, Control)

**Problem**: macOS restricts access to sensitive directories (Desktop, Documents, Downloads, etc.)

**Check Permissions**:
```bash
# Full Disk Access status
tccutil reset All  # Reset all permissions (requires SIP disabled)

# Check if app has permission via system_profiler
system_profiler SPApplicationsDataType | grep -A 5 "AppName"
```

**Handling Permission Errors**:
```python
import os
import sys

def check_tcc_access(path: str) -> bool:
    """Check if we have TCC permission for a path."""
    try:
        os.listdir(path)
        return True
    except PermissionError:
        return False

def request_permission_prompt(resource: str) -> None:
    """Guide user to grant permission."""
    print(f"""
    This app needs access to {resource}.
    
    To grant access:
    1. Open System Settings > Privacy & Security > {resource}
    2. Click + and add this application
    3. Restart the app
    """)
    sys.exit(1)
```

---

## Keychain Access

**Pattern**: Store secrets in Keychain, not config files.

```python
import subprocess
import json

def keychain_get(service: str, account: str) -> str | None:
    """Get password from Keychain."""
    result = subprocess.run([
        'security', 'find-generic-password',
        '-s', service,
        '-a', account,
        '-w'  # Output password only
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def keychain_set(service: str, account: str, password: str) -> bool:
    """Store password in Keychain."""
    # Delete existing first (update not supported)
    subprocess.run([
        'security', 'delete-generic-password',
        '-s', service,
        '-a', account
    ], capture_output=True)
    
    result = subprocess.run([
        'security', 'add-generic-password',
        '-s', service,
        '-a', account,
        '-w', password
    ], capture_output=True)
    
    return result.returncode == 0
```

---

## Notification Center Integration

**Pattern**: Use native notifications instead of print statements for user-facing tools.

```python
import subprocess

def notify(title: str, message: str, sound: str = "default") -> None:
    """Send macOS notification."""
    script = f'''
    display notification "{message}" with title "{title}" sound name "{sound}"
    '''
    subprocess.run(['osascript', '-e', script])

# Usage
notify("Backup Complete", "Backed up 1,234 files successfully")
```

**Alternative with terminal-notifier**:
```bash
brew install terminal-notifier

terminal-notifier -title "Backup" -message "Complete" -sound default
```

---

## App Bundling Patterns

**When**: Distributing Python/Node apps to non-developers.

**PyInstaller** (Python):
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "MyApp" main.py
# Output: dist/MyApp.app
```

**pkg-based installer**:
```bash
# Create package
pkgbuild --root ./dist --identifier com.example.myapp --version 1.0 MyApp.pkg

# Create DMG
hdiutil create -volname "MyApp" -srcfolder ./dist -ov -format UDZO MyApp.dmg
```

---

## Homebrew Formula Pattern

**When**: Distributing CLI tools.

**Formula template** (`Formula/mytool.rb`):
```ruby
class Mytool < Formula
  desc "Description of my tool"
  homepage "https://github.com/username/mytool"
  url "https://github.com/username/mytool/archive/v1.0.0.tar.gz"
  sha256 "abc123..."
  license "MIT"

  depends_on "python@3.12"

  def install
    bin.install "mytool.py" => "mytool"
  end

  test do
    system "#{bin}/mytool", "--version"
  end
end
```

**Tap installation**:
```bash
brew tap username/tap
brew install mytool
```

---

## System Integrity Protection (SIP) Awareness

**Never require SIP disabled** for normal operation.

**What SIP Protects**:
- `/System/`
- `/usr/` (except `/usr/local/`)
- `/bin/`, `/sbin/`
- System apps

**Safe Locations**:
- `/usr/local/` (Homebrew)
- `~/Library/` (user data)
- `/Library/` (system-wide, but not protected)
- `/Applications/` (apps)

---

## Quick Reference: macOS Paths

```bash
# User directories
~/Library/Application Support/AppName/  # App data
~/Library/Preferences/                   # Plists
~/Library/Caches/AppName/               # Caches (can be deleted)
~/Library/Logs/AppName/                 # Logs

# System directories
/Library/Application Support/           # System-wide app data
/usr/local/bin/                         # User-installed binaries
/opt/homebrew/bin/                      # Homebrew on Apple Silicon

# Temp
$TMPDIR                                 # Per-user temp (cleaned on reboot)
/tmp/                                   # System temp
```
