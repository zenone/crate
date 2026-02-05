#!/bin/bash
# Quick Web UI Test Script

echo "================================================"
echo "  DJ MP3 Renamer - Web UI Quick Test"
echo "================================================"
echo ""

# Check dependencies
echo "1. Checking dependencies..."
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "⚠️  Installing web dependencies..."
    pip install -q -r requirements-web.txt
}
echo "✓ Dependencies ready"
echo ""

# Verify API
echo "2. Verifying API..."
python3 -c "from dj_mp3_renamer.api import RenamerAPI; print('✓ API accessible')"
echo ""

# Verify web server
echo "3. Verifying web server..."
python3 -c "from web.server import app; print('✓ Web server ready')"
echo ""

# Show instructions
echo "================================================"
echo "  Ready to launch!"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the server:"
echo "   python run_web.py"
echo ""
echo "2. Open your browser:"
echo "   http://localhost:8000"
echo ""
echo "3. Test features:"
echo "   • Toggle dark/light mode (sun/moon icon)"
echo "   • Upload MP3 files (drag & drop or browse)"
echo "   • Preview rename results"
echo "   • Execute rename"
echo ""
echo "4. Read full testing guide:"
echo "   WEB_UI_TESTING.md"
echo ""
echo "================================================"
echo ""
echo "Press any key to launch server, or Ctrl+C to exit..."
read -n 1 -s

echo ""
echo "Launching server..."
echo ""
python run_web.py
