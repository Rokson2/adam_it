# Adam Architecture

## Components

### Python Agent

The main user-facing component that handles:
- CLI interface (Typer)
- Agent loop (LLM ↔ Tool cycle)
- Model routing (complexity-based)
- Memory management (Mem0)
- Tool execution

### Go Runtime

The security layer that handles:
- Container management (Docker/Firecracker)
- Security profile enforcement
- Path validation
- Audit logging

### Communication

Python and Go communicate via gRPC over Unix domain sockets:
- Low latency
- No network exposure
- OS-level access control

## Data Flow

```
User Input → CLI → Agent Loop → Model Router → LLM Provider
                                        ↓
                               Tool Call Decision
                                        ↓
                          Runtime Client → gRPC → Go Runtime
                                        ↓
                          Container Execution → Result
                                        ↓
User Response ← Agent Loop ← Tool Result
```

## Memory System

**Short-term (Session)**
- In-memory conversation history
- Max 50 messages
- Per-session scope

**Long-term (Mem0)**
- Chroma vector database
- Semantic search
- Persistent across sessions

## Model Routing

Three execution modes:
1. **Auto-pilot**: Complexity estimation → tier → model
2. **Workflow**: Pre-defined model per step
3. **Manual**: User-specified model

Complexity tiers:
- **Quick**: Haiku-class models for simple lookups
- **Standard**: Sonnet-class for implementation
- **Deep**: Opus-class for architecture/debugging
