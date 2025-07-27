#!/bin/bash

# SPY-FLY macOS Setup Script (Modern Best Practices with uv)
# Uses uv for fast, reliable Python package management

set -euo pipefail

echo "🔧 SPY-FLY macOS Setup (Modern)"
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

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_color "$YELLOW" "📦 Installing uv (modern Python package manager)..."
    brew install uv
    print_color "$GREEN" "✅ uv installed successfully"
else
    print_color "$BLUE" "✅ uv is already installed"
fi

# Check architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    print_color "$BLUE" "🍎 Apple Silicon (M1/M2/M3) detected"
else
    print_color "$BLUE" "🖥️  Intel Mac detected"
fi

# Backend setup with uv
print_color "$BLUE" "🐍 Setting up Python backend with uv..."
cd backend

# Remove old pip-based venv if it exists
if [[ -d "venv" ]] && [[ ! -f ".venv/uv.lock" ]]; then
    print_color "$YELLOW" "⚠️  Removing old pip-based virtual environment..."
    rm -rf venv .venv
fi

# Create virtual environment with uv
if [[ ! -d ".venv" ]]; then
    print_color "$BLUE" "Creating virtual environment with uv..."
    uv venv
fi

# Install dependencies with uv (MUCH faster than pip)
print_color "$BLUE" "Installing Python dependencies with uv (this will be fast!)..."
uv pip install -r requirements.txt

print_color "$GREEN" "✅ Backend setup complete (with uv)"
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

# Create pyproject.toml for modern Python project management
if [[ ! -f "backend/pyproject.toml" ]]; then
    print_color "$BLUE" "Creating pyproject.toml for modern Python tooling..."
    cat > backend/pyproject.toml << 'EOF'
[tool.uv]
dev-dependencies = [
    "pytest>=8.2.2",
    "pytest-asyncio>=0.23.7",
    "black>=24.4.2",
    "ruff>=0.5.1",
]

[tool.black]
line-length = 88
target-version = ["py311", "py312", "py313"]

[tool.ruff]
line-length = 88
target-version = "py311"
select = ["E", "F", "B", "Q", "I"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
EOF
fi

print_color "$GREEN" "✅ Setup complete!"
echo ""
echo "Benefits of using uv:"
echo "  • 8-10x faster package installation"
echo "  • Better handling of Apple Silicon wheels"
echo "  • No more Python version conflicts"
echo "  • Modern, Rust-based tooling"
echo ""
echo "To start the servers, run: ./start.sh"
echo ""