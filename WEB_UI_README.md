# DJ MP3 Renamer - Web UI

Modern, clean web interface for the DJ MP3 Renamer with dark/light mode support.

## Features

- 🎨 **Dark/Light Mode** - Automatic system preference detection + manual toggle
- 📁 **Drag & Drop Upload** - Modern file upload with visual feedback
- 🎵 **Template System** - Customize filename patterns with live preview
- ⚡ **Fast & Responsive** - Built with FastAPI for high performance
- 🔒 **API-First Architecture** - Web layer wraps existing API (no modifications)
- 📱 **Mobile Friendly** - Responsive design for all screen sizes

## Tech Stack

- **Backend:** FastAPI (async Python web framework)
- **Frontend:** Vanilla HTML/CSS/JavaScript (no build step required)
- **Styling:** Modern CSS with CSS Variables for theming
- **Icons:** Inline SVG (Feather Icons style)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements-web.txt
```

This installs:
- `fastapi` - Modern web framework
- `uvicorn` - ASGI server
- `python-multipart` - File upload support
- `aiofiles` - Async file handling

### 2. Verify API is Installed

```bash
python3 -c "from dj_mp3_renamer.api import RenamerAPI; print('API OK')"
```

## HTTPS Support 🔒

The web UI **automatically sets up HTTPS** with trusted certificates for localhost!

### First Run (Automatic Setup)

```bash
./start_web_ui.sh
```

**What happens:**
1. Script checks if `mkcert` is installed
2. If not, prompts to install it automatically (one-time setup)
3. Generates trusted SSL certificates for localhost
4. Starts server at **https://localhost:8000** (green padlock, no warnings!)

**Total user interaction:** Press Enter once. That's it!

### Subsequent Runs

```bash
./start_web_ui.sh
```

Server starts instantly at **https://localhost:8000** — certificates persist across restarts.

### HTTP Fallback

If certificate generation fails or you prefer HTTP:

```bash
./start_web_ui.sh --no-https
```

Server falls back gracefully to **http://localhost:8000**

### Why HTTPS on Localhost?

- **Future-proof**: Modern web APIs require secure contexts (Service Workers, Web Audio, camera/microphone)
- **Production parity**: Test in conditions matching real-world deployment
- **Zero friction**: `mkcert` eliminates browser warnings and manual trust store editing
- **Professional**: Green padlock inspires confidence

### Troubleshooting

**mkcert not found:**
- macOS: `brew install mkcert`
- Linux: `sudo apt install mkcert` or `sudo dnf install mkcert`
- Windows: `choco install mkcert` or `scoop install mkcert`
- Manual: https://github.com/FiloSottile/mkcert#installation

**Certificate generation failed:**
- Check system permissions (mkcert requires admin/sudo for CA installation)
- Ensure mkcert CA is installed: `mkcert -CAROOT`
- Re-run: `./start_web_ui.sh --force`

**Browser still shows warning:**
- Firefox users: mkcert should auto-configure, but if not, manually trust the CA
- Check mkcert installation: `mkcert -install`

---

## Usage

### Quick Start

```bash
# Launch web server (HTTPS with auto-provisioning)
./start_web_ui.sh

# Force HTTP mode
./start_web_ui.sh --no-https

# Force restart (stops existing instance first)
./start_web_ui.sh --force
```

Then open your browser to **https://localhost:8000** (or http if using --no-https)

### Step-by-Step Workflow

1. **Upload MP3 Files**
   - Drag & drop MP3 files onto the upload zone
   - Or click "Browse Files" to select files

2. **Configure Template**
   - Use the default template or customize it
   - Available tokens: `{artist}`, `{title}`, `{bpm}`, `{camelot}`, etc.
   - Click "Preview Changes" to see results without renaming

3. **Review & Execute**
   - Preview shows what files will be renamed
   - Click "Rename Files" to execute
   - View results with success/skip/error counts

4. **Start New Batch**
   - Click "Start New Batch" to process more files

## Architecture

```
Browser (Frontend)
       ↓
FastAPI Server (web/server.py)
       ↓
dj_mp3_renamer.api (UNCHANGED)
       ↓
Core Modules
```

### Directory Structure

```
web/
├── __init__.py
├── server.py              # FastAPI application
├── static/
│   ├── css/
│   │   └── styles.css     # Dark/light mode CSS
│   └── js/
│       └── app.js         # Frontend logic
├── templates/
│   └── index.html         # Main UI
└── uploads/               # Temporary file storage
```

## API Endpoints

The web server exposes these REST endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve main HTML page |
| `/api/upload` | POST | Upload MP3 files |
| `/api/rename` | POST | Execute rename operation |
| `/api/templates` | GET | Get available template tokens |
| `/api/session/{id}` | DELETE | Clean up session |
| `/api/health` | GET | Health check |

## Dark/Light Mode

### How It Works

- **System Detection:** Automatically uses your OS theme preference
- **Manual Toggle:** Click sun/moon icon in header to switch
- **Persistent:** Saves preference to localStorage

### Implementation

- Uses CSS Custom Properties (CSS Variables)
- Respects `prefers-color-scheme` media query
- Smooth transitions between themes
- WCAG 3.0 compliant contrast ratios

### Color Palette

**Light Mode:**
- Background: `#ffffff`
- Secondary: `#f8f9fa`
- Text: `#212529`

**Dark Mode:**
- Background: `#0f172a` (soft black, not pure black)
- Secondary: `#1e293b`
- Text: `#f1f5f9` (off-white)

## Development

### Running in Development Mode

```bash
# Auto-reload on file changes
python run_web.py --reload
```

### Testing the Web UI

1. **Upload Test**
   ```bash
   # Create test MP3s
   mkdir -p /tmp/test_mp3s
   cp ~/Music/test.mp3 /tmp/test_mp3s/
   ```

2. **Open Browser**
   - Navigate to http://localhost:8000
   - Upload test files
   - Try preview mode
   - Execute rename

3. **Theme Toggle**
   - Click sun/moon icon
   - Verify smooth transition
   - Check localStorage persistence

### Code Quality

```bash
# Format code
black web/

# Type checking (if using mypy)
mypy web/server.py

# Lint
ruff check web/
```

## Customization

### Change Theme Colors

Edit `web/static/css/styles.css`:

```css
:root {
    --primary: #your-color;  /* Brand color */
    --bg-primary: #your-bg;   /* Main background */
}
```

### Change Port

```bash
python run_web.py --port 3000
```

### Add New Routes

Edit `web/server.py`:

```python
@app.get("/your-route")
async def your_function():
    return {"message": "Hello"}
```

## Troubleshooting

### Port Already in Use

```bash
# Use different port
python run_web.py --port 8001
```

### Import Errors

```bash
# Ensure you're in project root
cd /path/to/batch_rename

# Verify API is accessible
python3 -c "import dj_mp3_renamer.api"
```

### Files Not Uploading

- Check file is .mp3 extension
- Verify `web/uploads/` directory exists
- Check browser console for errors

### Theme Not Persisting

- Check browser localStorage is enabled
- Try clearing localStorage: `localStorage.clear()`

## Performance

- **Async Operations:** FastAPI handles uploads/renames asynchronously
- **Session-Based:** Each upload gets unique session ID
- **Auto-Cleanup:** Sessions can be cleaned up via API
- **Concurrent Renames:** Uses existing API's ThreadPoolExecutor

## Security Notes

- **Local Use:** Designed for local/trusted networks
- **No Authentication:** Add auth if exposing to internet
- **File Uploads:** Limited to .mp3 files
- **Session Isolation:** Each upload session is isolated

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Modern mobile browsers

**Required Features:**
- CSS Grid & Flexbox
- ES6+ JavaScript
- Fetch API
- CSS Custom Properties

## Contributing

The web UI is a separate layer from the core API. When adding features:

1. **DO NOT** modify `dj_mp3_renamer/api/` or `dj_mp3_renamer/core/`
2. **DO** add new routes to `web/server.py`
3. **DO** keep frontend logic in `web/static/js/app.js`
4. **DO** follow existing CSS patterns for theming

## Future Enhancements

Potential features:

- [ ] Download renamed files as ZIP
- [ ] Batch template presets
- [ ] Advanced filtering options
- [ ] Undo rename operations
- [ ] Integration with music services
- [ ] Real-time progress bar
- [ ] Keyboard shortcuts
- [ ] Accessibility improvements

## Credits

- **Icons:** Feather Icons style (inline SVG)
- **Framework:** FastAPI by Sebastián Ramírez
- **Design:** Inspired by modern file upload UX patterns

## License

Same license as main project (MIT).
