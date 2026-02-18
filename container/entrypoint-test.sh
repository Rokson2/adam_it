#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════"
echo "  Adam Test Environment"
echo "════════════════════════════════════════════════════════"

# Initialize directories
mkdir -p $ADAM_HOME/{data,logs,memory,vault,workspace}

# Start runtime in background
echo "Starting Adam Runtime..."
adam-runtime --profile balanced --profiles /root/.adam/profiles &
RUNTIME_PID=$!

# Wait for runtime
sleep 2

# Check if vault needs setup
if [ ! -f "$ADAM_HOME/vault/secrets.enc" ]; then
    echo ""
    echo "⚠️  Vault not initialized. Run: adam vault unlock"
    echo ""
fi

echo ""
echo "Adam is ready!"
echo ""
echo "Commands:"
echo "  adam --help          Show all commands"
echo "  adam vault unlock    Initialize vault"
echo "  adam agent start     Start interactive chat"
echo "  adam profile list    List security profiles"
echo ""

# Keep container running
if [ "$1" = "bash" ]; then
    exec bash
else
    exec "$@"
fi
