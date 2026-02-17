"""
Ollama provider for local LLM inference.
"""

import httpx
import json
from typing import List, Dict, AsyncIterator, Optional
from .base import BaseProvider, Message, CompletionResponse, ToolCall


class OllamaProvider(BaseProvider):
    """Provider for Ollama local LLM."""

    name = "ollama"

    def __init__(self, api_base: str = "http://localhost:11434", **kwargs):
        self.api_base = api_base

    async def complete(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> CompletionResponse:
        async with httpx.AsyncClient() as client:
            payload = {
                "model": model,
                "messages": self.format_messages_for_provider(messages),
                "stream": False,
                "options": {
                    "num_predict": kwargs.get("max_tokens", 4096),
                },
            }

            response = await client.post(
                f"{self.api_base}/api/chat",
                json=payload,
                timeout=300.0,
            )
            response.raise_for_status()
            data = response.json()

            return CompletionResponse(
                content=data["message"]["content"],
                tool_calls=[],
                finish_reason="stop",
                usage={},
                model=model,
            )

    async def stream(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            payload = {
                "model": model,
                "messages": self.format_messages_for_provider(messages),
                "stream": True,
            }

            async with client.stream(
                "POST",
                f"{self.api_base}/api/chat",
                json=payload,
                timeout=300.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass

    async def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/api/tags", timeout=5.0)
                return response.status_code == 200
        except:
            return False

    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/api/tags", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except:
            return []
