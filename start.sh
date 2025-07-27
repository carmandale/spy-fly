#!/bin/bash

# SPY-FLY Development Server Startup Script
# This script starts both the backend FastAPI server and frontend React dev server

echo "🚀 Starting SPY-FLY Trading Dashboard..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Check if backend port 8000 is already in use
if check_port 8000; then
    echo -e "${RED}⚠️  Port 8000 is already in use. Please stop the existing process first.${NC}"
    echo "Run: lsof -ti:8000 | xargs kill -9"
    exit 1
fi

# Check if frontend port 5173 is already in use
if check_port 5173; then
    echo -e "${RED}⚠️  Port 5173 is already in use. Please stop the existing process first.${NC}"
    echo "Run: lsof -ti:5173 | xargs kill -9"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "spy-fly-prd.md" ]; then
    echo -e "${RED}Error: Please run this script from the spy-fly project root directory${NC}"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check Node installation
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p logs

# Start backend server
echo -e "${BLUE}Starting Backend Server...${NC}"
cd backend

# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
    # Check if uvicorn is installed
    if ! python -m pip show uvicorn &> /dev/null; then
        echo "Installing backend dependencies..."
        pip install -r requirements.txt
    fi
else
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
fi

# Start backend in background and save PID
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if check_port 8000; then
    echo -e "${GREEN}✓ Backend server started on http://localhost:8000${NC}"
else
    echo -e "${RED}✗ Backend server failed to start. Check logs/backend.log${NC}"
    exit 1
fi

# Start frontend server
echo -e "${BLUE}Starting Frontend Server...${NC}"
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend in background and save PID
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 3

# Check if frontend started successfully
if check_port 5173; then
    echo -e "${GREEN}✓ Frontend server started on http://localhost:5173${NC}"
else
    echo -e "${RED}✗ Frontend server failed to start. Check logs/frontend.log${NC}"
    # Kill backend if frontend fails
    kill $BACKEND_PID
    exit 1
fi

# Save PIDs to file for shutdown script
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo ""
echo -e "${GREEN}🎉 SPY-FLY is running!${NC}"
echo ""
echo "📊 Dashboard: http://localhost:5173"
echo "🔧 API Docs: http://localhost:8000/docs"
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
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    rm -f .backend.pid .frontend.pid
    echo "Servers stopped."
    exit 0
}

# Trap Ctrl+C
trap shutdown INT

# Keep script running
while true; do
    sleep 1
done