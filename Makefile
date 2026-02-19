.PHONY: all install build test clean fmt help proto

all: build

install:
	@./install.sh

build: build-go
	@echo "Installing Python agent..."
	@cd python-agent && pip install -e . --break-system-packages 2>/dev/null || pip install -e . --user 2>/dev/null || pipx install -e . 2>/dev/null || (echo "Run: sudo apt install pipx && pipx install -e ." && exit 1)
	@echo "✓ Build complete"

build-go:
	@echo "Building Go runtime..."
	@cd go-runtime && go mod tidy && go build -o bin/adam-runtime ./cmd/adam-runtime

test:
	@cd go-runtime && go test ./...
	@cd python-agent && python3 -m pytest tests/ -v

clean:
	@rm -rf go-runtime/bin/ python-agent/build/ python-agent/dist/ python-agent/*.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

fmt:
	@cd go-runtime && go fmt ./...
	@cd python-agent && black adam tests 2>/dev/null || true

proto:
	@cd go-runtime && protoc --go_out=. --go_opt=paths=source_relative --go-grpc_out=. --go-grpc_opt=paths=source_relative proto/adam.proto
	@cd python-agent && python3 -m grpc_tools.protoc -I../go-runtime/proto --python_out=adam/runtime --grpc_python_out=adam/runtime ../go-runtime/proto/adam.proto

help:
	@echo "Adam Makefile"
	@echo ""
	@echo "  make install   - Full installation"
	@echo "  make build     - Build Go + Python"
	@echo "  make build-go  - Build Go runtime only"
	@echo "  make test      - Run tests"
	@echo "  make clean     - Clean artifacts"
	@echo "  make proto     - Regenerate protobuf"
