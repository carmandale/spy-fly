#!/bin/bash

# SPY-FLY Server Shutdown Script

echo "🛑 Stopping SPY-FLY servers..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Stop backend server
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill $BACKEND_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Backend server stopped${NC}"
    else
        echo -e "${RED}⚠️  Backend server was not running${NC}"
    fi
    rm -f .backend.pid
else
    # Try to find and kill by port
    if lsof -ti:8000 >/dev/null 2>&1; then
        lsof -ti:8000 | xargs kill -9
        echo -e "${GREEN}✓ Backend server stopped (by port)${NC}"
    else
        echo "Backend server was not running"
    fi
fi

# Stop frontend server
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill $FRONTEND_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Frontend server stopped${NC}"
    else
        echo -e "${RED}⚠️  Frontend server was not running${NC}"
    fi
    rm -f .frontend.pid
else
    # Try to find and kill by port
    if lsof -ti:5173 >/dev/null 2>&1; then
        lsof -ti:5173 | xargs kill -9
        echo -e "${GREEN}✓ Frontend server stopped (by port)${NC}"
    else
        echo "Frontend server was not running"
    fi
fi

echo ""
echo "All servers stopped."