# DJ MP3 Renamer - Web UI

Modern web interface for batch renaming DJ MP3 files with metadata-based templates.

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn
```

### 2. Run the Server

```bash
# From the project root directory
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
source .venv/bin/activate
python -m uvicorn web.main:app --reload
```

### 3. Open in Browser

Navigate to: http://localhost:8000

## Manual Testing Checkpoints

### ✅ Checkpoint 1: Basic Backend + Health Check (CURRENT)

**What to Test**:
1. Server starts without errors
2. Main page loads (http://localhost:8000)
3. API health endpoint works (http://localhost:8000/api/health)
4. No console errors in browser (F12)

**Expected Results**:
- See "DJ MP3 Renamer" page with glassmorphism dark theme
- API Status shows "Ready" in green
- Version shows "1.0.0"
- /api/health returns JSON: `{"status": "ok", "version": "1.0.0", "api": "ready"}`

---

### 🔄 Checkpoint 2: Core Backend + File Browser (NEXT)

**Coming Soon**:
- Directory browsing
- File selection
- Metadata display
- API endpoints for preview, rename, config

**Estimated**: 3-4 hours

---

### 🔄 Checkpoint 3: Preview + Template Editor

**Coming Soon**:
- Template editor with validation
- Preview table
- Confirmation dialog

**Estimated**: 2-3 hours

---

### 🔄 Checkpoint 4: Progress + Async Operations

**Coming Soon**:
- Non-blocking rename execution
- Progress dialog
- Cancel functionality

**Estimated**: 2-3 hours

---

### 🔄 Checkpoint 5: Settings + Complete App

**Coming Soon**:
- Settings page
- Metadata analyzer
- Full polish

**Estimated**: 2-3 hours

## Architecture

### Backend
- **Framework**: FastAPI (async support)
- **Server**: Uvicorn (ASGI)
- **API**: RESTful endpoints + WebSocket (future)

### Frontend
- **HTML5**: Semantic structure
- **CSS3**: Glassmorphism, dark mode, responsive
- **JavaScript**: Vanilla ES6+ (no frameworks)

### File Structure
```
web/
├── main.py              # FastAPI application
├── static/
│   ├── index.html       # Main SPA
│   ├── css/
│   │   └── styles.css   # Modern styling
│   └── js/
│       ├── app.js       # Main application logic
│       ├── api.js       # API client
│       └── ui.js        # UI components (future)
└── README.md            # This file
```

## Development Tips

### Hot Reload
The `--reload` flag enables auto-restart on file changes:
```bash
python -m uvicorn web.main:app --reload
```

### Browser DevTools
- **F12**: Open DevTools
- **Network tab**: Monitor API calls
- **Console tab**: Check for JavaScript errors

### Testing API Endpoints
Use curl or browser:
```bash
curl http://localhost:8000/api/health
```

## Troubleshooting

### Server won't start
- Check if port 8000 is available
- Ensure virtual environment is activated
- Install missing dependencies: `pip install fastapi uvicorn`

### Static files not loading
- Check file paths are correct
- Clear browser cache (Cmd+Shift+R on Mac)
- Check browser console for 404 errors

### API errors
- Check server terminal for error messages
- Verify API endpoint paths
- Test with curl before testing in browser

## Next Steps

After Checkpoint 1 is verified:
1. Implement file browsing backend endpoints
2. Add directory selector UI
3. Display MP3 metadata
4. Move to Checkpoint 2 testing

## Support

For issues or questions, check:
- `.claude/OVERNIGHT_SESSION_SUMMARY.md` - Full project status
- `.claude/API_ENHANCEMENTS_SUMMARY.md` - API documentation
- Project root `README.md` - Overall project info
