#!/bin/bash
#
# Adam Installation Script
# One-line install: curl -fsSL https://raw.githubusercontent.com/Rokson2/adam_it/main/install.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin*)  OS="macos" ;;
    Linux*)   OS="linux" ;;
    *)        echo -e "${RED}Unsupported OS: $OS${NC}"; exit 1 ;;
esac

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAM_VENV="$HOME/.adam/venv"

echo -e "${GREEN}Installing Adam on $OS...${NC}"

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Python 3
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 is required. Please install it first.${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Python 3 found"
    
    # Python venv module
    if ! python3 -m venv --help &> /dev/null; then
        echo -e "${YELLOW}python3-venv not found. Installing...${NC}"
        if [ "$OS" = "linux" ]; then
            sudo apt update && sudo apt install -y python3-venv python3-pip
        fi
    fi
    echo -e "  ${GREEN}✓${NC} Python venv available"
    
    # Go
    if ! command -v go &> /dev/null; then
        echo -e "${YELLOW}Go not found. Installing...${NC}"
        if [ "$OS" = "macos" ]; then
            brew install go
        else
            echo -e "${YELLOW}Please install Go: https://go.dev/doc/install${NC}"
            echo "  On Ubuntu/Debian: sudo apt install -y golang-go"
            exit 1
        fi
    fi
    echo -e "  ${GREEN}✓${NC} Go found"
    
    # Docker (optional but recommended)
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}Docker not found. Container features will be limited.${NC}"
        echo -e "  Install Docker: https://docs.docker.com/get-docker/"
    else
        echo -e "  ${GREEN}✓${NC} Docker found"
    fi
}

# Install Go runtime
install_go_runtime() {
    echo "Building Go runtime..."
    cd "$SCRIPT_DIR/go-runtime"
    
    go mod tidy
    go build -o bin/adam-runtime ./cmd/adam-runtime
    
    # Symlink to /usr/local/bin
    sudo ln -sf "$(pwd)/bin/adam-runtime" /usr/local/bin/adam-runtime
    
    cd "$SCRIPT_DIR"
    echo -e "  ${GREEN}✓${NC} Go runtime installed"
}

# Install Python agent in virtual environment
install_python_agent() {
    echo "Installing Python agent..."
    
    # Create virtual environment
    mkdir -p "$HOME/.adam"
    
    if [ ! -d "$ADAM_VENV" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv "$ADAM_VENV"
    fi
    
    # Activate and install
    source "$ADAM_VENV/bin/activate"
    
    cd "$SCRIPT_DIR/python-agent"
    pip install --upgrade pip --quiet
    pip install -e . --quiet
    
    # Create wrapper script in /usr/local/bin
    cat > /tmp/adam-wrapper << WRAPPER
#!/bin/bash
source $ADAM_VENV/bin/activate
adam "\$@"
WRAPPER
    
    sudo mv /tmp/adam-wrapper /usr/local/bin/adam
    sudo chmod +x /usr/local/bin/adam
    
    cd "$SCRIPT_DIR"
    echo -e "  ${GREEN}✓${NC} Python agent installed"
}

# Initialize configuration
init_config() {
    echo "Initializing configuration..."
    
    ADAM_DIR="$HOME/.adam"
    mkdir -p "$ADAM_DIR"/{data,logs,memory,vault,workspace}
    
    # Create default config if not exists
    if [ ! -f "$ADAM_DIR/config.json" ]; then
        cat > "$ADAM_DIR/config.json" << 'CONFIG'
{
  "providers": {
    "anthropic": {
      "api_key": null
    },
    "openrouter": {
      "api_key": null
    },
    "ollama": {
      "api_base": "http://localhost:11434"
    }
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
  "profile": {
    "name": "balanced"
  }
}
CONFIG
        echo -e "  ${GREEN}✓${NC} Created default config"
    else
        echo -e "  ${GREEN}✓${NC} Config already exists"
    fi
}

# Copy security profiles
install_profiles() {
    echo "Installing security profiles..."
    
    ADAM_PROFILES="$HOME/.adam/profiles"
    mkdir -p "$ADAM_PROFILES"
    
    if [ -d "$SCRIPT_DIR/profiles" ]; then
        cp -r "$SCRIPT_DIR/profiles/"* "$ADAM_PROFILES/"
        echo -e "  ${GREEN}✓${NC} Profiles installed"
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Adam installed successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "  1. Start the runtime (in one terminal):"
    echo "     ${GREEN}adam-runtime${NC}"
    echo ""
    echo "  2. Run Adam dashboard (in another terminal):"
    echo "     ${GREEN}adam${NC}"
    echo ""
    echo "  The dashboard will guide you through:"
    echo "  - Creating a vault passphrase"
    echo "  - Adding your API key"
    echo ""
    echo "Documentation: https://github.com/Rokson2/adam_it#readme"
    echo ""
}

# Main
main() {
    check_prerequisites
    install_go_runtime
    install_python_agent
    install_profiles
    init_config
    print_success
}

main "$@"
