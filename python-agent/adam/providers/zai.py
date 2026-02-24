"""
z.ai (GLM) provider - simplified.

Uses OpenAI-compatible API. Model selection delegated to z.ai API.
"""

from typing import List, Dict
import httpx
import json

from .base import BaseProvider, Message, CompletionResponse, ToolCall


class ZaiProvider(BaseProvider):
    """Provider for z.ai (GLM) models via OpenAI-compatible API."""
    
    name = "z-ai"
    default_model = "glm-4-flash"  # Fast, good default
    api_base = "https://open.bigmodel.cn/api/paas/v4"
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key
    
    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        """Format messages for OpenAI-compatible API."""
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content
            })
        return formatted
    
    def _format_tools(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for OpenAI function calling."""
        if not tools:
            return None
        
        formatted = []
        for tool in tools:
            # OpenAI format
            if "type" in tool and "function" in tool:
                formatted.append(tool)
            # Anthropic format -> OpenAI
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
        """Complete using z.ai API."""
        
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
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            
            if response.status_code != 200:
                raise Exception(f"z.ai error: {response.status_code} - {response.text}")
            
            data = response.json()
        
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        
        # Parse tool calls
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


class ZaiCodingProvider(ZaiProvider):
    """z.ai Coding - same API, optimized for code."""
    
    name = "z-ai-coding"
    default_model = "glm-4-flash"  # Fast for coding iterations
