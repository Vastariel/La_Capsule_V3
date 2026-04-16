#!/bin/bash
# Verification Script for La Capsule V3
# Run this to check if everything is set up correctly

echo "=========================================="
echo "🔍 La Capsule V3 - System Verification"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} File exists: $1"
    else
        echo -e "${RED}✗${NC} File missing: $1"
        ((ERRORS++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Directory exists: $1"
    else
        echo -e "${RED}✗${NC} Directory missing: $1"
        ((ERRORS++))
    fi
}

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} Command available: $1"
    else
        echo -e "${RED}✗${NC} Command not found: $1"
        ((ERRORS++))
    fi
}

check_python_package() {
    python3 -c "import $1" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Python module installed: $1"
    else
        echo -e "${YELLOW}⚠${NC} Python module missing: $1"
        ((WARNINGS++))
    fi
}

# Check directory structure
echo "📁 Checking directory structure..."
check_dir "."
check_dir "bridge_python"
check_dir "bridge_python/utils"
check_dir "bridge_python/tests"
check_dir "raspi_controller"
check_dir "godot_ui"
check_dir "setup"
echo ""

# Check configuration files
echo "⚙️  Checking configuration files..."
check_file "setup/config.json"
check_file "bridge_python/requirements.txt"
check_file "bridge_python/config.py"
check_file "bridge_python/api.py"
check_file "bridge_python/gpio.py"
check_file "bridge_python/pico.py"
check_file "bridge_python/server.py"
check_file "bridge_python/main.py"
echo ""

# Check documentation
echo "📖 Checking documentation..."
check_file "README.md"
check_file "ARCHITECTURE.md"
check_file "QUICKSTART.md"
check_file "DEPLOYMENT.md"
check_file "SUMMARY.md"
echo ""

# Check Python environment
echo "🐍 Checking Python environment..."
check_command "python3"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "   Python version: $PYTHON_VERSION"
fi
echo ""

# Check basic Python packages
echo "📦 Checking Python packages..."
check_python_package "gpiozero"
check_python_package "websockets"
check_python_package "pigpio"
check_python_package "picod"
check_python_package "krpc"
echo ""

# Check configuration validity
echo "📋 Checking configuration..."
if python3 -c "import json; json.load(open('setup/config.json'))" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} config.json is valid JSON"
else
    echo -e "${RED}✗${NC} config.json has JSON errors"
    ((ERRORS++))
fi

# Check for required config keys
python3 << 'EOF'
import json
try:
    config = json.load(open('setup/config.json'))
    required_keys = ['network', 'hardware', 'performance']
    for key in required_keys:
        if key in config:
            print(f"✓ config.json has '{key}' section")
        else:
            print(f"✗ config.json missing '{key}' section")
except Exception as e:
    print(f"✗ Error reading config: {e}")
EOF
echo ""

# Summary
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
else
    echo -e "${RED}✗ $ERRORS error(s) found${NC}"
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found${NC}"
fi
echo "=========================================="
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "Next steps:"
    echo "1. Edit setup/config.json with your network IPs"
    echo "2. Follow QUICKSTART.md for setup instructions"
    echo "3. Run: python3 bridge_python/utils/config_loader.py"
else
    echo "Please fix the errors above before proceeding."
fi
echo ""
