#!/bin/bash
# Start the Crate web UI with HTTPS auto-config and smart instance management

set -e  # Exit on error

# Configuration
PIDFILE=".crate_web.pid"
LOGFILE="/tmp/crate-server.log"
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CERT_DIR="$PROJECT_DIR/certs"
CERT_FILE="$CERT_DIR/localhost.pem"
KEY_FILE="$CERT_DIR/localhost-key.pem"
PORT=8000

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cd "$PROJECT_DIR"

echo -e "${BLUE}🎵 Crate - Secure Startup${NC}"
echo "=============================="
echo ""

# Graceful shutdown handler
cleanup() {
    echo ""
    echo -e "${RED}🛑 Shutting down Crate...${NC}"

    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")

        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null || true

            # Wait up to 3 seconds for graceful shutdown
            for i in {1..3}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done

            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi

        rm -f "$PIDFILE"
        echo -e "${GREEN}✅ Server stopped${NC}"
    fi

    echo ""
    echo "Goodbye! 👋"
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# Function to install mkcert
install_mkcert() {
    echo -e "${YELLOW}⚠️  mkcert not found - HTTPS requires mkcert for trusted certificates.${NC}"
    echo ""
    echo -n "Would you like to install mkcert now? (recommended) [Y/n]: "
    read -r response

    if [[ "$response" =~ ^([yY][eE][sS]|[yY]|"")$ ]]; then
        # Detect OS and install
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command -v brew &> /dev/null; then
                echo -e "${BLUE}📦 Installing mkcert via Homebrew...${NC}"
                brew install mkcert
            else
                echo -e "${RED}✗ Homebrew not found. Please install mkcert manually:${NC}"
                echo "  Visit: https://github.com/FiloSottile/mkcert#installation"
                return 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            if command -v apt-get &> /dev/null; then
                echo -e "${BLUE}📦 Installing mkcert via apt...${NC}"
                sudo apt-get update && sudo apt-get install -y mkcert
            elif command -v dnf &> /dev/null; then
                echo -e "${BLUE}📦 Installing mkcert via dnf...${NC}"
                sudo dnf install -y mkcert
            elif command -v pacman &> /dev/null; then
                echo -e "${BLUE}📦 Installing mkcert via pacman...${NC}"
                sudo pacman -S mkcert
            else
                echo -e "${RED}✗ Package manager not found. Install mkcert manually:${NC}"
                echo "  Visit: https://github.com/FiloSottile/mkcert#installation"
                return 1
            fi
        else
            # Windows or other
            echo -e "${RED}✗ Unsupported OS. Please install mkcert manually:${NC}"
            echo "  Windows: choco install mkcert  OR  scoop install mkcert"
            echo "  Visit: https://github.com/FiloSottile/mkcert#installation"
            return 1
        fi

        echo -e "${GREEN}✓ mkcert installed successfully!${NC}"
        return 0
    else
        echo -e "${YELLOW}ℹ️  Skipping mkcert installation. Falling back to HTTP.${NC}"
        return 1
    fi
}

# Function to setup HTTPS certificates
setup_https() {
    # Check for --no-https flag
    if [ "$1" = "--no-https" ]; then
        echo -e "${YELLOW}ℹ️  HTTPS disabled via --no-https flag${NC}"
        return 1
    fi

    # Check if mkcert is installed
    if ! command -v mkcert &> /dev/null; then
        if ! install_mkcert; then
            return 1
        fi
    else
        echo -e "${GREEN}🔐 mkcert found! Setting up HTTPS...${NC}"
    fi

    # Install local CA if not already installed
    echo -e "${BLUE}🔐 Checking local certificate authority...${NC}"

    CA_ROOT=$(mkcert -CAROOT 2>/dev/null)
    CA_INSTALLED=false

    if [[ -n "$CA_ROOT" ]] && [[ -f "$CA_ROOT/rootCA.pem" ]]; then
        # CA exists, check if it's in system trust store
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS: Check system keychain
            if security find-certificate -c "mkcert" -a -Z /Library/Keychains/System.keychain 2>/dev/null | grep -q "mkcert"; then
                CA_INSTALLED=true
            fi
        else
            # Linux/Other: Assume installed if CA file exists
            CA_INSTALLED=true
        fi
    fi

    if [ "$CA_INSTALLED" = false ]; then
        echo -e "${BLUE}🔐 Installing local certificate authority...${NC}"
        echo -e "${YELLOW}   (You may be prompted for your password)${NC}"

        if mkcert -install; then
            echo -e "${GREEN}✓ Local CA installed in system trust store${NC}"
            echo -e "${YELLOW}   Note: Restart your browser for changes to take effect${NC}"
        else
            echo -e "${RED}✗ Failed to install CA. Try: mkcert -install${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✓ Local CA already installed${NC}"
    fi

    # Generate certificates if they don't exist
    if [[ ! -f "$CERT_FILE" ]] || [[ ! -f "$KEY_FILE" ]]; then
        echo -e "${BLUE}🎫 Generating localhost certificates...${NC}"
        mkdir -p "$CERT_DIR"

        cd "$CERT_DIR"
        mkcert -cert-file localhost.pem -key-file localhost-key.pem localhost 127.0.0.1 ::1
        chmod 600 localhost-key.pem
        cd "$PROJECT_DIR"

        echo -e "${GREEN}✓ Certificates created: $CERT_FILE${NC}"
    else
        echo -e "${GREEN}✓ Certificates already exist${NC}"
    fi

    echo ""
    return 0
}

# Auto-kill any existing instances (low friction!)
echo -e "${BLUE}🔍 Checking for existing server instances...${NC}"
EXISTING_PIDS=$(ps aux | grep -E "(uvicorn.*web\.main:app|python.*web/main\.py)" | grep -v grep | awk '{print $2}')

if [ -n "$EXISTING_PIDS" ]; then
    echo -e "${YELLOW}📍 Found existing server(s), stopping them automatically...${NC}"
    for pid in $EXISTING_PIDS; do
        kill $pid 2>/dev/null || true
    done
    sleep 1
    echo -e "${GREEN}✅ Cleaned up existing instances${NC}"
fi

rm -f "$PIDFILE" 2>/dev/null || true
echo ""

# Attempt HTTPS setup
HTTPS_ENABLED=false
PROTOCOL="http"
if setup_https "$@"; then
    HTTPS_ENABLED=true
    PROTOCOL="https"
else
    echo -e "${YELLOW}⚠️  Could not set up HTTPS${NC}"
    echo -e "${YELLOW}ℹ️  Falling back to HTTP mode${NC}"
    echo ""
fi

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found (.venv)${NC}"
    echo "Please create it with: python -m venv .venv"
    exit 1
fi

source .venv/bin/activate

# Find available port
check_port() {
    lsof -i :$1 >/dev/null 2>&1
    return $?
}

MAX_PORT=8100
while check_port $PORT; do
    echo -e "${YELLOW}⚠️  Port $PORT in use, trying next port...${NC}"
    PORT=$((PORT + 1))
    if [ $PORT -gt $MAX_PORT ]; then
        echo -e "${RED}❌ Could not find available port in range 8000-$MAX_PORT${NC}"
        exit 1
    fi
done

# Build uvicorn command based on HTTPS
if [ "$HTTPS_ENABLED" = true ]; then
    UVICORN_CMD="python -m uvicorn web.main:app --host 127.0.0.1 --port $PORT --ssl-keyfile $KEY_FILE --ssl-certfile $CERT_FILE --reload"
else
    UVICORN_CMD="python -m uvicorn web.main:app --host 127.0.0.1 --port $PORT --reload"
fi

# Start the server
echo -e "${GREEN}✅ Found available port: $PORT${NC}"
echo -e "${GREEN}✅ Starting Crate...${NC}"
echo ""
echo -e "${BLUE}📍 URL: $PROTOCOL://127.0.0.1:$PORT${NC}"
echo "📝 Log: $LOGFILE"
echo ""

if [ "$HTTPS_ENABLED" = true ]; then
    echo -e "${GREEN}🔒 HTTPS enabled - No browser warnings!${NC}"
else
    echo -e "${YELLOW}🔓 HTTP mode${NC}"
fi

echo ""
echo "Press Ctrl+C to stop (or use ./stop_crate_web.sh)"
echo ""

# Start uvicorn in background and save PID
$UVICORN_CMD > "$LOGFILE" 2>&1 &
SERVER_PID=$!

# Save PID
echo $SERVER_PID > "$PIDFILE"

# Wait and verify it started
sleep 2

if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server started successfully!${NC}"
    echo "   PID: $SERVER_PID"
    echo "   Port: $PORT"
    echo "   Protocol: $PROTOCOL"
    echo ""
    echo -e "${BLUE}🌐 URL: $PROTOCOL://127.0.0.1:$PORT${NC}"
    echo ""

    # Auto-open browser
    URL="$PROTOCOL://127.0.0.1:$PORT"
    echo -e "${BLUE}🚀 Opening browser at: $URL${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$URL" 2>&1 || echo "   (Could not auto-open - please open manually)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$URL" 2>&1 || echo "   (Could not auto-open - please open manually)"
    else
        echo "   (Auto-open not supported - please open manually)"
    fi

    echo ""
    echo -e "${YELLOW}📋 Server logs (Ctrl+C to stop):${NC}"
    echo ""

    # Follow the log
    tail -f "$LOGFILE"
else
    echo -e "${RED}❌ Server failed to start. Check log:${NC}"
    cat "$LOGFILE"
    rm -f "$PIDFILE"
    exit 1
fi
