#!/bin/bash

# SPY-FLY Dashboard Sanity Check Script
# Runs Playwright tests to verify UI is working

set -euo pipefail

echo "🧪 Running SPY-FLY Dashboard Sanity Check..."
echo ""

# Colors
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[0;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_color() {
    printf "%b%s%b\n" "$1" "$2" "$NC"
}

# Check if servers are running
check_servers() {
    local backend_running=false
    local frontend_running=false
    
    # Load environment variables
    if [ -f backend/.env ]; then
        export $(cat backend/.env | grep -v '^#' | xargs)
    fi
    BACKEND_PORT=${API_PORT:-8003}
    
    if lsof -nP -iTCP:$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
        backend_running=true
    fi
    
    # Load environment variables  
    if [ -f frontend/.env.local ]; then
        export $(cat frontend/.env.local | grep -v '^#' | xargs)
    fi
    FRONTEND_PORT=${PORT:-3003}
    
    if lsof -nP -iTCP:$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
        frontend_running=true
    fi
    
    if [[ "$backend_running" == false ]] || [[ "$frontend_running" == false ]]; then
        print_color "$YELLOW" "⚠️  Servers not running. Starting them now..."
        ./start.sh &
        SERVER_PID=$!
        sleep 10  # Give servers time to start
        
        # Verify they started
        if ! lsof -nP -iTCP:$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
            print_color "$RED" "❌ Backend failed to start"
            exit 1
        fi
        
        if ! lsof -nP -iTCP:$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
            print_color "$RED" "❌ Frontend failed to start"
            exit 1
        fi
        
        print_color "$GREEN" "✅ Servers started"
        return 0
    else
        print_color "$GREEN" "✅ Servers already running"
        return 1
    fi
}

# Track if we started servers
STARTED_SERVERS=false
if check_servers; then
    STARTED_SERVERS=true
fi

# Run tests
print_color "$BLUE" "🎭 Running Playwright UI tests..."
cd frontend

# Install browsers if not already installed
if [[ ! -d "$HOME/Library/Caches/ms-playwright" ]]; then
    print_color "$YELLOW" "Installing Playwright browsers..."
    npx playwright install
fi

# Run the tests
if npm run test:e2e; then
    print_color "$GREEN" "✅ All UI tests passed!"
    
    # Show summary
    echo ""
    print_color "$GREEN" "Dashboard Sanity Check Results:"
    echo "  • Dashboard loads correctly"
    echo "  • All main components visible"
    echo "  • Sentiment panel displays data"
    echo "  • Market status bar works"
    echo "  • Responsive design verified"
    echo "  • No console errors detected"
else
    print_color "$RED" "❌ Some tests failed"
    echo "Check the test report for details"
fi

# Clean up if we started servers
if [[ "$STARTED_SERVERS" == true ]] && [[ -n "${SERVER_PID:-}" ]]; then
    echo ""
    print_color "$YELLOW" "Stopping test servers..."
    kill $SERVER_PID 2>/dev/null || true
    sleep 2
    cd ..
    ./stop.sh
fi

cd ..

echo ""
print_color "$BLUE" "💡 To view detailed test results:"
echo "  cd frontend && npx playwright show-report"