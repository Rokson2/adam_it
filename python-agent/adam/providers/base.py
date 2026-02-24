"""
Base provider interface - simplified.

Philosophy (inspired by NanoClaw):
- No hardcoded model lists
- Delegate model selection to SDKs
- "auto" = use provider's default
- Let providers add new models without code changes
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, AsyncIterator


@dataclass
class ToolCall:
    """A tool call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class CompletionResponse:
    """Response from LLM completion."""
    content: str
    tool_calls: List[ToolCall]
    finish_reason: str = "stop"
    usage: Dict[str, int] = None
    model: str = ""
    
    def __post_init__(self):
        if self.usage is None:
            self.usage = {"input_tokens": 0, "output_tokens": 0}


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # "system", "user", "assistant"
    content: str


class BaseProvider(ABC):
    """
    Base class for LLM providers.
    
    Simple interface - just complete messages with optional tools.
    Model selection is delegated to the provider/SDK.
    """
    
    name: str = "base"
    default_model: str = "auto"
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        model: str = "auto",
        tools: List[Dict] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Complete a conversation.
        
        Args:
            messages: List of messages in conversation
            model: Model to use (or "auto" for provider default)
            tools: Optional list of tools in provider's format
            **kwargs: Additional provider-specific options
        
        Returns:
            CompletionResponse with content and optional tool calls
        """
        pass
    
    async def stream(
        self,
        messages: List[Message],
        model: str = "auto",
        tools: List[Dict] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion. Optional - default falls back to complete().
        """
        response = await self.complete(messages, model, tools, **kwargs)
        yield response.content
    
    def supports_tools(self) -> bool:
        """Whether this provider supports tool calling."""
        return True
    
    def supports_vision(self) -> bool:
        """Whether this provider supports image input."""
        return False
    
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.default_model
    
    def resolve_model(self, model: str) -> str:
        """
        Resolve model name.
        
        - "auto" -> provider's default
        - anything else -> pass through (let API validate)
        """
        if model in ("auto", ""):
            return self.default_model
        return model
