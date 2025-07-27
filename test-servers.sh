#!/bin/bash

echo "Testing SPY-FLY servers manually..."

# Test backend
echo "Starting backend..."
cd backend
source venv/bin/activate 2>/dev/null
python -m uvicorn app.main:app --port 8000 &
BACKEND_PID=$!
cd ..

sleep 3

# Check if backend is running
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✓ Backend is working!"
else
    echo "✗ Backend failed to start"
fi

# Test frontend
echo "Starting frontend..."
cd frontend
npm run dev -- --port 5173 &
FRONTEND_PID=$!
cd ..

sleep 5

# Check if frontend is running
if curl -s http://localhost:5173 > /dev/null; then
    echo "✓ Frontend is working!"
else
    echo "✗ Frontend failed to start"
fi

# Cleanup
echo "Stopping servers..."
kill $BACKEND_PID 2>/dev/null
kill $FRONTEND_PID 2>/dev/null

echo "Test complete!"