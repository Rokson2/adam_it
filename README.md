# ADAM - Personal AI Assistant

A local-first, security-focused personal AI assistant with containerized script execution and encrypted storage.

**Author:** Arbeey (arbeey@proton.me)

## Features

- **Secure File Access**: Path-based access control with user-selectable security profiles
- **Containerized Execution**: Scripts run in isolated Docker/Firecracker containers
- **Encrypted Storage**: All secrets and memory stored locally with encryption
- **Multi-Provider LLM**: Support for Anthropic, OpenRouter, Ollama, and more
- **Intelligent Routing**: Automatic model selection based on task complexity
- **Persistent Memory**: Long-term semantic memory via Mem0 + Chroma
- **Scheduled Tasks**: Cron-like scheduling for automated workflows
- **Interactive Dashboard**: User-friendly CLI with setup guidance and HUD

## Quick Start

### Prerequisites

- Python 3.11+
- Go 1.21+
- Docker (or Firecracker on Linux)

### Install

```bash
# Clone
git clone https://github.com/Rokson2/adam_it.git
cd adam_it

# Install
make install

# Or manually
cd go-runtime && go build -o ~/.local/bin/adam-runtime ./cmd/adam-runtime
cd ../python-agent && pip install -e .
```

### Initialize

```bash
# Start runtime (in one terminal)
adam-runtime &

# Run Adam dashboard
adam
```

First run will guide you through:
1. Creating a vault passphrase
2. Adding an API key for your LLM provider

### Using Docker

```bash
docker-compose -f docker-compose.test.yml up -d
docker exec -it adam-test bash
# Inside container:
export ADAM_VAULT_PASSPHRASE=your-password
adam
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

## Supported LLM Providers

| Provider | Description |
|----------|-------------|
| Anthropic | Claude 3.5 Sonnet, Haiku, Opus |
| OpenAI | GPT-4, GPT-4 Turbo |
| OpenRouter | 100+ models via single API |
| DeepSeek | DeepSeek Chat, Coder |
| Ollama | Local models (no API key needed) |

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
│   │   ├── security/     # Secure key storage
│   │   ├── storage/      # Database + Vault
│   │   └── tools/        # Tool implementations
│   └── pyproject.toml
├── profiles/             # Security profiles
└── container/            # Docker test environment
```

## Development

```bash
# Run tests
make test

# Build all
make build

# Format code
make fmt

# Generate protobuf files
make proto
```

## License

MIT

## Author

Arbeey - [arbeey@proton.me](mailto:arbeey@proton.me)
