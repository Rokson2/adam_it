# Adam - Personal AI Assistant

A local-first, security-focused personal AI assistant with containerized script execution and encrypted storage.

## Features

- **Secure File Access**: Path-based access control with user-selectable security profiles
- **Containerized Execution**: Scripts run in isolated Docker/Firecracker containers
- **Encrypted Storage**: All secrets and memory stored locally with encryption
- **Multi-Provider LLM**: Support for Anthropic, OpenRouter, Ollama, and more
- **Intelligent Routing**: Automatic model selection based on task complexity
- **Persistent Memory**: Long-term semantic memory via Mem0 + Chroma
- **Scheduled Tasks**: Cron-like scheduling for automated workflows

## Quick Start

### Prerequisites

- Python 3.11+
- Go 1.21+
- Docker (or Firecracker on Linux)

### Install

```bash
# Clone
git clone https://github.com/yourname/adam.git
cd adam

# Install
make install

# Or manually
cd go-runtime && go build -o bin/adam-runtime ./cmd/adam-runtime
cd ../python-agent && pip install -e .
```

### Initialize

```bash
# Unlock vault
adam vault unlock

# Add API key
adam vault add ANTHROPIC_API_KEY

# Start runtime (in one terminal)
adam-runtime

# Chat (in another terminal)
adam agent start
```

## Usage

### Interactive Chat

```bash
adam agent start
```

### Single Message

```bash
adam ask "What files are in my Documents folder?"
```

### Scheduled Tasks

```bash
# Add daily task
adam cron add -n "morning-briefing" -s "0 9 * * *" -m "Summarize my calendar for today"

# List tasks
adam cron list
```

### Security Profiles

```bash
# List profiles
adam profile list

# Show profile details
adam profile info balanced

# Switch profile
adam profile set paranoid
```

### Backup

```bash
# Export
adam sync export -o backup.tar.gz

# Import
adam sync import backup.tar.gz
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLI (Typer)                    │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                 Agent Loop                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Router   │  │ Memory   │  │ Tool Layer   │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ gRPC
┌──────────────────────▼──────────────────────────┐
│              Go Runtime                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Security │  │Container │  │   Auditor    │  │
│  │ Profiles │  │ Manager  │  │              │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────┘
```

## Security Profiles

| Profile | Isolation | File Access | Use Case |
|---------|-----------|-------------|----------|
| Balanced | Docker | Limited read/write | Daily use |
| Paranoid | Firecracker | Explicit grants only | Untrusted code |
| Permissive | None | Full home | Trusted environments |

## Configuration

Config file: `~/.adam/config.json`

```json
{
  "providers": {
    "anthropic": {
      "api_key": "from-vault"
    },
    "ollama": {
      "api_base": "http://localhost:11434"
    }
  },
  "agent": {
    "default_mode": "auto_pilot",
    "tier_models": {
      "quick": "claude-3-haiku",
      "standard": "claude-3.5-sonnet",
      "deep": "claude-opus-4"
    }
  }
}
```

## Project Structure

```
adam/
├── go-runtime/           # Go container runtime
│   ├── cmd/              # Entry points
│   ├── internal/         # Packages
│   └── proto/            # gRPC definitions
├── python-agent/         # Python agent
│   ├── adam/
│   │   ├── agent/        # Agent loop
│   │   ├── cli/          # CLI commands
│   │   ├── config/       # Configuration
│   │   ├── memory/       # Memory system
│   │   ├── orchestration/# Model routing
│   │   ├── providers/    # LLM providers
│   │   ├── runtime/      # gRPC client
│   │   ├── storage/      # Database + Vault
│   │   └── tools/        # Tool implementations
│   └── pyproject.toml
├── profiles/             # Security profiles
└── docs/                 # Documentation
```

## Development

```bash
# Run tests
make test

# Build all
make build

# Format code
make fmt
```

## License

MIT
