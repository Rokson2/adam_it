.PHONY: all install build test clean fmt help

# Default target
all: build

# Install everything
install:
	@echo "Installing Adam..."
	@./install.sh

# Build all components
build: build-go build-python
	@echo "✓ Build complete"

build-go:
	@echo "Building Go runtime..."
	cd go-runtime && go mod tidy && go build -o bin/adam-runtime ./cmd/adam-runtime

build-python:
	@echo "Installing Python package..."
	cd python-agent && pip install -e . --quiet

# Run tests
test: test-go test-python
	@echo "✓ All tests passed"

test-go:
	cd go-runtime && go test ./...

test-python:
	cd python-agent && python3 -m pytest tests/ -v

# Format code
fmt: fmt-go fmt-python
	@echo "✓ Code formatted"

fmt-go:
	cd go-runtime && go fmt ./...

fmt-python:
	cd python-agent && black adam tests

# Clean build artifacts
clean:
	rm -rf go-runtime/bin/
	rm -rf python-agent/build/ python-agent/dist/ python-agent/*.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Run linter
lint:
	cd go-runtime && go vet ./...
	cd python-agent && ruff check adam/

# Generate proto files
proto:
	cd go-runtime && \
	protoc --go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		proto/adam.proto
	cd python-agent && \
	python3 -m grpc_tools.protoc \
		-I../go-runtime/proto \
		--python_out=adam/runtime \
		--grpc_python_out=adam/runtime \
		../go-runtime/proto/adam.proto

# Development mode
dev:
	@echo "Starting development environment..."
	@./bin/start-dev.sh

# Help
help:
	@echo "Adam Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install     Install Adam (run install.sh)"
	@echo "  build       Build all components"
	@echo "  test        Run all tests"
	@echo "  fmt         Format code"
	@echo "  clean       Remove build artifacts"
	@echo "  lint        Run linters"
	@echo "  proto       Generate gRPC code from proto files"
	@echo "  help        Show this help"
