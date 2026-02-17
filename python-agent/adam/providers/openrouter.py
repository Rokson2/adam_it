"""
OpenRouter provider - access to multiple LLM providers.
"""

import httpx
import json
from typing import List, Dict, AsyncIterator, Optional
from .base import BaseProvider, Message, CompletionResponse, ToolCall


class OpenRouterProvider(BaseProvider):
    """Provider for OpenRouter API."""

    name = "openrouter"

    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url or "https://openrouter.ai/api/v1"

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
                "max_tokens": kwargs.get("max_tokens", 4096),
            }
            if tools:
                payload["tools"] = tools

            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://adam.ai",
                    "X-Title": "Adam Assistant",
                },
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            tool_calls = []

            if choice.get("message", {}).get("tool_calls"):
                for tc in choice["message"]["tool_calls"]:
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        args = json.loads(args)
                    tool_calls.append(
                        ToolCall(
                            id=tc["id"],
                            name=tc["function"]["name"],
                            arguments=args,
                        )
                    )

            return CompletionResponse(
                content=choice["message"]["content"] or "",
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", "stop"),
                usage=data.get("usage", {}),
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
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://adam.ai",
                },
                json=payload,
                timeout=120.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices"):
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            pass
