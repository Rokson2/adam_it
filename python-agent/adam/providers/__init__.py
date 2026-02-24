"""
LLM Providers - simplified.

Each provider handles its own model selection.
Use "auto" for sensible defaults.
"""

from .base import (
    BaseProvider,
    Message,
    CompletionResponse,
    ToolCall,
)

from .registry import (
    get_provider,
    list_providers,
    load_keys_from_vault,
    ProviderRegistry,
)

__all__ = [
    "BaseProvider",
    "Message", 
    "CompletionResponse",
    "ToolCall",
    "get_provider",
    "list_providers",
    "load_keys_from_vault",
    "ProviderRegistry",
]
