#!/bin/bash

# SPY-FLY Server Shutdown Script

set -euo pipefail  # Exit on error, undefined variables, pipe failures

echo "🛑 Stopping SPY-FLY servers..."

# Colors for output
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    printf "%b%s%b\n" "$color" "$message" "$NC"
}

# Function to stop process by PID file
stop_by_pid_file() {
    local pid_file=$1
    local service_name=$2
    
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(<"$pid_file")
        
        # Check if process is actually running
        if kill -0 "$pid" 2>/dev/null; then
            # Try graceful shutdown first
            if kill -TERM "$pid" 2>/dev/null; then
                # Wait up to 5 seconds for graceful shutdown
                local count=0
                while kill -0 "$pid" 2>/dev/null && [[ $count -lt 5 ]]; do
                    sleep 1
                    ((count++))
                done
                
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    kill -9 "$pid" 2>/dev/null
                    print_color "$YELLOW" "⚠️  $service_name server required force stop"
                else
                    print_color "$GREEN" "✓ $service_name server stopped gracefully"
                fi
            fi
        else
            print_color "$YELLOW" "⚠️  $service_name server was not running (stale PID)"
        fi
        rm -f "$pid_file"
    else
        # No PID file, try to find by port
        return 1
    fi
    return 0
}

# Function to stop process by port
stop_by_port() {
    local port=$1
    local service_name=$2
    
    # Get PIDs listening on the port
    local pids
    pids=$(lsof -ti:$port 2>/dev/null || true)
    
    if [[ -n "$pids" ]]; then
        # Try graceful shutdown first
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        
        # Wait a moment
        sleep 2
        
        # Force kill any remaining
        local remaining
        remaining=$(lsof -ti:$port 2>/dev/null || true)
        if [[ -n "$remaining" ]]; then
            echo "$remaining" | xargs kill -9 2>/dev/null || true
            print_color "$YELLOW" "⚠️  $service_name server required force stop"
        else
            print_color "$GREEN" "✓ $service_name server stopped"
        fi
        return 0
    else
        print_color "$YELLOW" "$service_name server was not running"
        return 1
    fi
}

# Stop backend server
if ! stop_by_pid_file ".backend.pid" "Backend"; then
    stop_by_port 8001 "Backend"
fi

# Stop frontend server
if ! stop_by_pid_file ".frontend.pid" "Frontend"; then
    stop_by_port 5174 "Frontend"
fi

# Clean up any orphaned log files
if [[ -d "logs" ]]; then
    # Keep logs but truncate if they're too large (>10MB)
    find logs -name "*.log" -size +10M -exec truncate -s 0 {} \;
fi

echo ""
print_color "$GREEN" "All servers stopped."