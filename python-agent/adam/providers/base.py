"""
Base provider interface for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Message:
    """A chat message."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    """A tool/function call from the LLM."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class CompletionResponse:
    """Response from LLM completion."""

    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""


class BaseProvider(ABC):
    """Base class for LLM providers."""

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> CompletionResponse:
        """
        Complete a chat conversation.

        Args:
            messages: List of conversation messages
            model: Model identifier
            tools: Available tools in provider format
            **kwargs: Additional provider-specific options

        Returns:
            CompletionResponse with content and optional tool calls
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion.

        Yields:
            Chunks of content as they're generated
        """
        pass

    def format_messages_for_provider(self, messages: List[Message]) -> List[Dict]:
        """Format messages for this provider's API."""
        return [{"role": m.role, "content": m.content} for m in messages]

    def format_tools_for_provider(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for this provider's API."""
        return tools
