"""z.ai (GLM) provider - OpenAI-compatible API.

CONFIRMED MODELS (from API testing):
- glm-4-plus, glm-4-air, glm-4-flash, glm-4-long, glm-4v

NOTE: GLM-4.7 and GLM-5 were mentioned but exact model IDs need confirmation.
Please verify with https://open.bigmodel.cn/dev/api and update if needed.
"""

import httpx
import json
from typing import List, Dict, AsyncIterator, Optional
from .base import BaseProvider, Message, CompletionResponse, ToolCall


class ZaiProvider(BaseProvider):
    """Provider for z.ai (GLM) models using OpenAI-compatible API."""
    
    name = "z-ai"
    
    ZAI_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    
    # Confirmed working models
    VALID_MODELS = [
        "glm-4-plus",      # Best quality
        "glm-4-air",       # Balanced
        "glm-4-airx",      # Extended air
        "glm-4-flash",     # Fastest
        "glm-4-flashx",    # Extended flash
        "glm-4-long",      # Long context
        "glm-4v",          # Vision
        "glm-4v-plus",     # Enhanced vision
        "glm-4",           # Standard
        "glm-3-turbo",     # Legacy
    ]
    
    DEFAULT_MODEL = "glm-4-flash"
    
    def __init__(self, api_key: str = None, api_base: str = None, **kwargs):
        self.api_key = api_key
        self.api_base = api_base or self.ZAI_API_BASE
    
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def _format_messages(self, messages: List[Message]) -> List[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]
    
    def _format_tools(self, tools: List[Dict]) -> List[Dict]:
        if not tools:
            return []
        formatted = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    }
                })
        return formatted
    
    def _resolve_model(self, model: str) -> str:
        if model in self.VALID_MODELS:
            return model
        if model == "auto":
            return self.DEFAULT_MODEL
        # Map common names
        mapping = {
            "quick": "glm-4-flash",
            "standard": "glm-4-air",
            "deep": "glm-4-plus",
            "claude-3-haiku": "glm-4-flash",
            "claude-3-sonnet": "glm-4-air",
            "gpt-4": "glm-4-plus",
        }
        return mapping.get(model.lower(), self.DEFAULT_MODEL)
    
    async def complete(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> CompletionResponse:
        api_model = self._resolve_model(model)
        
        payload = {
            "model": api_model,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        if tools:
            formatted = self._format_tools(tools)
            if formatted:
                payload["tools"] = formatted
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            
            if response.status_code != 200:
                raise Exception(f"{response.status_code} - {response.text}")
            
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
                    arguments=args,
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
            model=api_model,
        )


class ZaiCodingProvider(ZaiProvider):
    """z.ai Coding provider."""
    
    name = "z-ai-coding"
    DEFAULT_MODEL = "glm-4-flash"  # Fast for coding
