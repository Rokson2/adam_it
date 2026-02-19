#!/bin/bash
#
# Adam Installation Script
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin*)  OS="macos" ;;
    Linux*)   OS="linux" ;;
    *)        echo -e "${RED}Unsupported OS: $OS${NC}"; exit 1 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}Installing Adam on $OS...${NC}"

check_prerequisites() {
    echo "Checking prerequisites..."
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 is required.${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Python 3: $(python3 --version)"
    
    if ! command -v go &> /dev/null; then
        echo -e "${RED}Go is required. Install with: sudo apt install -y golang-go${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Go: $(go version)"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}⚠ Docker not found (optional)${NC}"
    else
        echo -e "  ${GREEN}✓${NC} Docker found"
    fi
}

install_go_runtime() {
    echo "Building Go runtime..."
    cd "$SCRIPT_DIR/go-runtime"
    go mod tidy
    go build -o bin/adam-runtime ./cmd/adam-runtime
    sudo ln -sf "$(pwd)/bin/adam-runtime" /usr/local/bin/adam-runtime
    cd "$SCRIPT_DIR"
    echo -e "  ${GREEN}✓${NC} Go runtime installed to /usr/local/bin/adam-runtime"
}

install_python_agent() {
    echo "Installing Python agent..."
    cd "$SCRIPT_DIR/python-agent"
    
    # Try pipx first (cleanest for CLI apps)
    if command -v pipx &> /dev/null; then
        echo "  Using pipx..."
        pipx install -e . --force
        echo -e "  ${GREEN}✓${NC} Installed via pipx"
        return 0
    fi
    
    # Try direct pip with --break-system-packages (modern pip)
    if pip install -e . --break-system-packages 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Installed directly"
        return 0
    fi
    
    # Fallback: try --user
    if pip install -e . --user 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Installed with --user"
        return 0
    fi
    
    # Last resort: suggest pipx
    echo -e "${YELLOW}Direct install blocked. Installing pipx...${NC}"
    sudo apt install -y pipx
    pipx ensurepath
    source ~/.bashrc 2>/dev/null || true
    pipx install -e . --force
    echo -e "  ${GREEN}✓${NC} Installed via pipx"
}

init_config() {
    echo "Initializing configuration..."
    
    ADAM_DIR="$HOME/.adam"
    mkdir -p "$ADAM_DIR"/{data,logs,memory,vault,workspace,profiles}
    
    if [ ! -f "$ADAM_DIR/config.json" ]; then
        cat > "$ADAM_DIR/config.json" << 'CONFIG'
{
  "providers": {
    "anthropic": {"api_key": null},
    "openrouter": {"api_key": null},
    "ollama": {"api_base": "http://localhost:11434"}
  },
  "agent": {
    "default_mode": "auto_pilot",
    "tier_models": {
      "quick": "claude-3-haiku-20240307",
      "standard": "claude-3-5-sonnet-20241022",
      "deep": "claude-sonnet-4-20250514"
    },
    "workspace": "~/.adam/workspace"
  },
  "profile": {"name": "balanced"}
}
CONFIG
        echo -e "  ${GREEN}✓${NC} Config created"
    else
        echo -e "  ${GREEN}✓${NC} Config exists"
    fi
    
    # Copy profiles
    if [ -d "$SCRIPT_DIR/profiles" ]; then
        cp -r "$SCRIPT_DIR/profiles/"* "$ADAM_DIR/profiles/"
        echo -e "  ${GREEN}✓${NC} Profiles installed"
    fi
}

print_success() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✓ Adam installed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Start:"
    echo "  ${GREEN}adam-runtime &${NC}   # Start runtime"
    echo "  ${GREEN}adam${NC}             # Run dashboard"
    echo ""
    echo "Docs: https://github.com/Rokson2/adam_it"
    echo ""
}

main() {
    check_prerequisites
    install_go_runtime
    install_python_agent
    init_config
    print_success
}

main "$@"
