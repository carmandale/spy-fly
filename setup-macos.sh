#!/bin/bash

# SPY-FLY macOS Setup Script
# Ensures proper Python environment for macOS

set -euo pipefail

echo "🔧 SPY-FLY macOS Setup"
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

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    print_color "$RED" "❌ Homebrew is not installed"
    echo "Install with: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
print_color "$BLUE" "📦 Current Python version: $PYTHON_VERSION"

# Warn if using Python 3.13+
if [[ "$PYTHON_VERSION" == "3.13" ]]; then
    print_color "$YELLOW" "⚠️  Python 3.13 detected. This is very new and may cause slow dependency installation."
    echo "Pandas and numpy may need to build from source, which can take 10-15 minutes."
    echo ""
    echo "For faster installation, consider using Python 3.11 or 3.12:"
    echo "  brew install python@3.12"
    echo "  python3.12 -m venv backend/venv"
    echo ""
    read -p "Continue with Python 3.13? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    print_color "$BLUE" "🍎 Apple Silicon (M1/M2/M3) detected"
else
    print_color "$BLUE" "🖥️  Intel Mac detected"
fi

# Backend setup
print_color "$BLUE" "🐍 Setting up Python backend..."
cd backend

# Remove old venv if switching Python versions
if [[ -d "venv" ]] && [[ -f "venv/bin/python" ]]; then
    VENV_PYTHON_VERSION=$(venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ "$VENV_PYTHON_VERSION" != "$PYTHON_VERSION" ]]; then
        print_color "$YELLOW" "⚠️  Removing old venv (was Python $VENV_PYTHON_VERSION)"
        rm -rf venv
    fi
fi

# Create venv if needed
if [[ ! -d "venv" ]]; then
    print_color "$BLUE" "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate and upgrade pip
source venv/bin/activate
print_color "$BLUE" "Upgrading pip..."
pip install --quiet --upgrade pip wheel setuptools

# Install with progress indication
print_color "$BLUE" "Installing Python dependencies..."
if [[ "$PYTHON_VERSION" == "3.13" ]] && [[ "$ARCH" == "arm64" ]]; then
    print_color "$YELLOW" "⏳ This may take 5-10 minutes on Python 3.13 + Apple Silicon..."
fi

# Try to use only binary packages when possible
pip install --prefer-binary -r requirements.txt

print_color "$GREEN" "✅ Backend setup complete"
deactivate
cd ..

# Frontend setup
print_color "$BLUE" "📦 Setting up Node.js frontend..."
cd frontend

# Check Node version
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v)
    print_color "$BLUE" "Node.js version: $NODE_VERSION"
else
    print_color "$RED" "❌ Node.js not found"
    echo "Install with: brew install node"
    exit 1
fi

# Install frontend dependencies
if [[ ! -d "node_modules" ]]; then
    print_color "$BLUE" "Installing frontend dependencies..."
    npm install
else
    print_color "$GREEN" "✅ Frontend dependencies already installed"
fi

cd ..

# Create .env files if needed
if [[ ! -f "backend/.env" ]]; then
    print_color "$BLUE" "Creating backend .env file..."
    cat > backend/.env << EOF
# Polygon.io API Configuration
POLYGON_API_KEY=your_polygon_api_key_here
POLYGON_USE_SANDBOX=true

# Application Settings
DEBUG=true
DATABASE_URL=sqlite:///./spy_fly.db
EOF
    print_color "$YELLOW" "⚠️  Remember to add your Polygon.io API key to backend/.env"
fi

print_color "$GREEN" "✅ Setup complete!"
echo ""
echo "To start the servers, run: ./start.sh"
echo ""

# Offer to install recommended Python version if using 3.13
if [[ "$PYTHON_VERSION" == "3.13" ]]; then
    echo "For better compatibility, you can install Python 3.12:"
    echo "  brew install python@3.12"
    echo "  rm -rf backend/venv"
    echo "  python3.12 -m venv backend/venv"
    echo "  ./setup-macos.sh"
fi