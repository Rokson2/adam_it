"""
OpenRouter provider - simplified.

OpenRouter provides access to many models via unified API.
Model selection delegated to OpenRouter.
"""

from typing import List, Dict
import httpx
import json

from .base import BaseProvider, Message, CompletionResponse, ToolCall


class OpenRouterProvider(BaseProvider):
    """Provider for OpenRouter (many models via one API)."""
    
    name = "openrouter"
    default_model = "anthropic/claude-3.5-sonnet"
    api_base = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key
    
    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        return [{"role": m.role, "content": m.content} for m in messages]
    
    def _format_tools(self, tools: List[Dict]) -> List[Dict]:
        if not tools:
            return None
        
        formatted = []
        for tool in tools:
            if "type" in tool and "function" in tool:
                formatted.append(tool)
            elif "input_schema" in tool:
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }
                })
        
        return formatted if formatted else None
    
    async def complete(
        self,
        messages: List[Message],
        model: str = "auto",
        tools: List[Dict] = None,
        **kwargs
    ) -> CompletionResponse:
        
        resolved_model = self.resolve_model(model)
        
        payload = {
            "model": resolved_model,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            payload["tools"] = formatted_tools
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/adam",
            "X-Title": "Adam"
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenRouter error: {response.status_code} - {response.text}")
            
            data = response.json()
        
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        
        tool_calls = []
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                args = tc.get("function", {}).get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except:
                        args = {}
                tool_calls.append(ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    arguments=args
                ))
        
        usage = data.get("usage", {})
        
        return CompletionResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
            model=data.get("model", resolved_model)
        )
