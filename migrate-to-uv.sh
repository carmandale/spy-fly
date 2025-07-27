#!/bin/bash

# Migrate from pip to uv for existing SPY-FLY installations
# Following modern macOS best practices

set -euo pipefail

echo "🔄 Migrating SPY-FLY to use uv (modern Python package manager)"
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

# Install uv if not present
if ! command -v uv &> /dev/null; then
    print_color "$BLUE" "📦 Installing uv..."
    brew install uv
    print_color "$GREEN" "✅ uv installed"
fi

# Navigate to backend
cd backend

# Check if old venv exists
if [[ -d "venv" ]]; then
    print_color "$YELLOW" "📁 Found existing pip-based virtual environment"
    
    # Extract installed packages
    if [[ -f "venv/bin/pip" ]]; then
        print_color "$BLUE" "📋 Saving current package list..."
        venv/bin/pip freeze > requirements-freeze.txt
    fi
    
    # Backup old venv
    print_color "$BLUE" "💾 Backing up old virtual environment..."
    mv venv venv.pip-backup
    
    # Create new uv-based environment
    print_color "$BLUE" "🚀 Creating new virtual environment with uv..."
    uv venv
    
    # Install packages with uv
    print_color "$BLUE" "📦 Installing packages with uv (this will be FAST!)..."
    uv pip install -r requirements.txt
    
    print_color "$GREEN" "✅ Migration complete!"
    echo ""
    echo "Old pip-based venv backed up to: backend/venv.pip-backup"
    echo "You can safely delete it with: rm -rf backend/venv.pip-backup"
    echo ""
    echo "Benefits you'll notice:"
    echo "  • Package installation is now 8-10x faster"
    echo "  • No more build issues on Apple Silicon"
    echo "  • Better dependency resolution"
    
    # Clean up
    rm -f requirements-freeze.txt
else
    print_color "$YELLOW" "⚠️  No existing pip virtual environment found"
    echo "Running fresh setup with uv..."
    uv venv
    uv pip install -r requirements.txt
    print_color "$GREEN" "✅ Setup complete with uv!"
fi

cd ..

print_color "$GREEN" "🎉 Migration complete!"
echo ""
echo "Next steps:"
echo "1. Run ./start.sh to start the servers"
echo "2. All future installs will use uv automatically"
echo ""