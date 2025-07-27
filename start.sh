#!/bin/bash

# SPY-FLY Development Server Startup Script (Modern with uv)
# Uses uv for Python package management following macOS best practices

set -euo pipefail  # Exit on error, undefined variables, pipe failures

echo "🚀 Starting SPY-FLY Trading Dashboard..."
echo ""

# Colors for output (using printf for better compatibility)
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly RED='\033[0;31m'
readonly NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to check if a port is in use (macOS compatible)
check_port() {
    if lsof -nP -iTCP:"$1" -sTCP:LISTEN &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    printf "%b%s%b\n" "$color" "$message" "$NC"
}

# SPY-FLY uses unique ports to avoid conflicts
# Backend: 8003, Frontend: 3003

# Check if backend port is already in use
BACKEND_PORT=8003
if check_port $BACKEND_PORT; then
    print_color "$RED" "⚠️  Port $BACKEND_PORT is already in use. Please stop the existing process first."
    echo "Run: lsof -ti:$BACKEND_PORT | xargs kill -9"
    exit 1
fi

# Check if frontend port is already in use
FRONTEND_PORT=3003
if check_port $FRONTEND_PORT; then
    print_color "$RED" "⚠️  Port $FRONTEND_PORT is already in use. Please stop the existing process first."
    echo "Run: lsof -ti:$FRONTEND_PORT | xargs kill -9"
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "spy-fly-prd.md" ]]; then
    print_color "$RED" "Error: Please run this script from the spy-fly project root directory"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_color "$RED" "Error: uv is not installed"
    echo "Install with: brew install uv"
    echo "Or run: ./setup-macos.sh"
    exit 1
fi

# Check Node installation
if ! command -v node &> /dev/null; then
    print_color "$RED" "Error: Node.js is not installed"
    echo "Install with: brew install node"
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p logs

# Start backend server
print_color "$BLUE" "Starting Backend Server..."
(
    cd backend || exit 1
    
    # Check if .venv exists (uv creates .venv, not venv)
    if [[ -d ".venv" ]]; then
        # shellcheck disable=SC1091
        source .venv/bin/activate
        # Check if uvicorn is installed
        if ! python -m pip show uvicorn &> /dev/null; then
            echo "Installing backend dependencies with uv..."
            uv pip install -r requirements.txt
        fi
    elif [[ -d "venv" ]]; then
        # Old pip-based venv exists, suggest migration
        print_color "$RED" "⚠️  Old pip-based virtual environment detected"
        echo "Run ./setup-macos.sh to migrate to uv (much faster!)"
        exit 1
    else
        echo "Creating virtual environment with uv..."
        uv venv
        # shellcheck disable=SC1091
        source .venv/bin/activate
        echo "Installing backend dependencies with uv..."
        uv pip install -r requirements.txt
    fi
    
    # Start backend with uvicorn directly, reading port from environment
    exec uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8003} --reload > ../logs/backend.log 2>&1
) &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend started successfully
if check_port $BACKEND_PORT; then
    print_color "$GREEN" "✓ Backend server started on http://localhost:$BACKEND_PORT"
else
    print_color "$RED" "✗ Backend server failed to start. Check logs/backend.log"
    exit 1
fi

# Start frontend server
print_color "$BLUE" "Starting Frontend Server..."
(
    cd frontend || exit 1
    
    # Install dependencies if needed
    if [[ ! -d "node_modules" ]]; then
        echo "Installing frontend dependencies..."
        npm install --silent
    fi
    
    # Start frontend with exec
    exec npm run dev > ../logs/frontend.log 2>&1
) &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

# Check if frontend started successfully
if check_port $FRONTEND_PORT; then
    print_color "$GREEN" "✓ Frontend server started on http://localhost:$FRONTEND_PORT"
else
    print_color "$RED" "✗ Frontend server failed to start. Check logs/frontend.log"
    # Kill backend if frontend fails
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Save PIDs to file for shutdown script
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo ""
print_color "$GREEN" "🎉 SPY-FLY is running!"
echo ""
echo "📊 Dashboard: http://localhost:$FRONTEND_PORT"
echo "🔧 API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "📝 Logs:"
echo "   Backend:  logs/backend.log"
echo "   Frontend: logs/frontend.log"
echo ""
echo "To stop the servers, press Ctrl+C or run: ./stop.sh"
echo ""

# Function to handle shutdown
shutdown() {
    echo ""
    echo "Shutting down servers..."
    
    # Send SIGTERM for graceful shutdown
    [[ -n "${BACKEND_PID:-}" ]] && kill -TERM "$BACKEND_PID" 2>/dev/null
    [[ -n "${FRONTEND_PID:-}" ]] && kill -TERM "$FRONTEND_PID" 2>/dev/null
    
    # Give processes time to shut down gracefully
    sleep 2
    
    # Force kill if still running
    [[ -n "${BACKEND_PID:-}" ]] && kill -9 "$BACKEND_PID" 2>/dev/null
    [[ -n "${FRONTEND_PID:-}" ]] && kill -9 "$FRONTEND_PID" 2>/dev/null
    
    rm -f .backend.pid .frontend.pid
    echo "Servers stopped."
    exit 0
}

# Trap signals for clean shutdown
trap shutdown INT TERM EXIT

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID