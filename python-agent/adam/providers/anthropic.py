"""
Anthropic Claude provider.
"""

import anthropic
from typing import List, Dict, AsyncIterator, Optional
from .base import BaseProvider, Message, CompletionResponse, ToolCall


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""

    name = "anthropic"

    def __init__(self, api_key: str = None, **kwargs):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def format_messages_for_provider(self, messages: List[Message]) -> tuple:
        """Format messages, extracting system prompt."""
        system = None
        formatted = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                formatted.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return system, formatted

    def format_tools_for_provider(self, tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI format to Anthropic format."""
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append(
                    {
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {}),
                    }
                )
        return anthropic_tools

    async def complete(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> CompletionResponse:
        system, formatted = self.format_messages_for_provider(messages)

        params = {
            "model": model,
            "messages": formatted,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if system:
            params["system"] = system
        if tools:
            params["tools"] = self.format_tools_for_provider(tools)

        response = await self.client.messages.create(**params)

        tool_calls = []
        content = ""

        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        return CompletionResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "stop",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            model=model,
        )

    async def stream(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        system, formatted = self.format_messages_for_provider(messages)

        params = {
            "model": model,
            "messages": formatted,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if system:
            params["system"] = system

        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text
