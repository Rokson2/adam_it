#!/bin/bash
# Adam Docker Test Script

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Adam Docker Test Environment${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""

# Check Docker
if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

echo "Step 1: Building Adam test image..."
docker-compose -f docker-compose.test.yml build

echo ""
echo "Step 2: Starting Adam container..."
docker-compose -f docker-compose.test.yml up -d

echo ""
echo "Step 3: Waiting for startup..."
sleep 3

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Adam is running!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
echo "To connect:"
echo "  docker exec -it adam-test bash"
echo ""
echo "Once inside, run:"
echo "  1. adam vault unlock"
echo "  2. adam vault add ANTHROPIC_API_KEY"
echo "  3. adam agent start"
echo ""
echo "To stop:"
echo "  docker-compose -f docker-compose.test.yml down"
echo ""
