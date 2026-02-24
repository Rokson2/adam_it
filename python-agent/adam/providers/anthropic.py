"""
Anthropic Claude provider - simplified.

Uses the official Anthropic SDK. Model selection is delegated to the SDK.
"""

from typing import List, Dict, Optional
import anthropic

from .base import BaseProvider, Message, CompletionResponse, ToolCall


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""
    
    name = "anthropic"
    default_model = "claude-sonnet-4-20250514"  # Good default for most tasks
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client
    
    def _format_messages(self, messages: List[Message]) -> tuple:
        """Format messages for Anthropic API. Returns (system, messages)."""
        system = ""
        formatted = []
        
        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                formatted.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return system, formatted
    
    def _format_tools(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for Anthropic API."""
        if not tools:
            return None
        
        formatted = []
        for tool in tools:
            # Already in Anthropic format?
            if "input_schema" in tool:
                formatted.append(tool)
            # Convert from OpenAI format
            elif "function" in tool:
                func = tool["function"]
                formatted.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object"})
                })
        
        return formatted if formatted else None
    
    async def complete(
        self,
        messages: List[Message],
        model: str = "auto",
        tools: List[Dict] = None,
        **kwargs
    ) -> CompletionResponse:
        """Complete using Anthropic API."""
        
        resolved_model = self.resolve_model(model)
        system, formatted_messages = self._format_messages(messages)
        formatted_tools = self._format_tools(tools)
        
        request_params = {
            "model": resolved_model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": formatted_messages,
        }
        
        if system:
            request_params["system"] = system
        
        if formatted_tools:
            request_params["tools"] = formatted_tools
        
        # Make synchronous call (Anthropic SDK is sync)
        response = self.client.messages.create(**request_params)
        
        # Extract content
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        
        # Extract tool calls
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {}
                ))
        
        return CompletionResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "stop",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            model=response.model
        )
