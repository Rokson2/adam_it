# Adam IT - Latest Update

**Date:** 2025-01-09
**Commit:** c7cd1f2

## Quick Start

### Docker (Mac)
```bash
cd /Users/rokbelej/kilo-test/adam
docker-compose -f docker-compose.test.yml up -d
docker exec -it adam-test bash

# Inside container:
export ADAM_VAULT_PASSPHRASE=test1234
adam
```

### Linux (Native)
```bash
cd ~/adam_it
git pull
adam-runtime &
export ADAM_VAULT_PASSPHRASE=your-password
adam
```

---

## Recent Changes

### Model Handling - Simplified (NanoClaw-inspired)

**Before:** 500+ lines of hardcoded model definitions
**After:** ~50 lines, providers handle model selection

- Removed `providers/models/` directory
- Removed `adam models` command
- Providers delegate to SDKs for model validation
- `"auto"` = use provider's sensible default
- New models work without code changes

### Providers

| Provider | Default Model | Notes |
|----------|---------------|-------|
| anthropic | claude-sonnet-4-20250514 | Full Claude 4 support |
| z-ai | glm-4-flash | GLM models via z.ai API |
| z-ai-coding | glm-4-flash | Optimized for coding |
| openrouter | anthropic/claude-3.5-sonnet | 100+ models |
| ollama | llama3.2 | Local models |

### Security

- API keys stored in encrypted vault (~/.adam/vault/)
- Keys never exposed to LLM prompts or tools
- `ADAM_VAULT_PASSPHRASE` env var for non-interactive use

### Dashboard

- Interactive setup on first run
- Status panel (vault, API keys)
- Setup checklist with progress
- Menu-driven interface

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Adam CLI                            │
├─────────────────────────────────────────────────────────┤
│  adam                    → Dashboard                     │
│  adam vault setup-api    → Add API key                   │
│  adam agent start        → Start interactive chat        │
│  adam ask "..."          → Single message                 │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Python Agent                           │
│  • Provider registry (simplified)                        │
│  • Tool execution (filesystem, shell, web)              │
│  • Session memory                                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼ (gRPC)
┌─────────────────────────────────────────────────────────┐
│                   Go Runtime                             │
│  • Container execution (Docker)                         │
│  • Security profiles                                     │
│  • Path validation                                       │
└─────────────────────────────────────────────────────────┘
```

---

## Files Structure

```
adam/
├── python-agent/
│   └── adam/
│       ├── cli/              # CLI commands
│       │   ├── main.py       # Entry point
│       │   ├── dashboard.py  # Interactive dashboard
│       │   └── commands/
│       │       ├── agent.py  # Chat commands
│       │       └── vault.py  # Secret management
│       ├── providers/        # LLM providers (simplified)
│       │   ├── base.py       # Base interface
│       │   ├── anthropic.py  # Claude
│       │   ├── zai.py        # z.ai/GLM
│       │   ├── openrouter.py # OpenRouter
│       │   └── registry.py   # Provider lookup
│       ├── agent/            # Agent loop
│       ├── security/         # Secure key storage
│       └── storage/          # Vault, database
├── go-runtime/               # Go container runtime
├── container/                # Docker config
└── profiles/                 # Security profiles
```

---

## Known Issues / TODO

1. **Weather tool not working** - Need to add web search/fetch tool
2. **z.ai GLM-4.7/GLM-5 models** - User to confirm exact model IDs
3. **HUD in chat** - Show provider/model info during chat
4. **Better error messages** - More actionable error suggestions

---

## Repository

- **GitHub:** https://github.com/Rokson2/adam_it
- **Author:** Arbeey (arbeey@proton.me)
- **License:** MIT
