"""z.ai (GLM) provider - OpenAI-compatible API.

Latest models (as of 2025):
- GLM-5 series: Latest generation
- GLM-4.7 series: Improved 4.x generation  
- GLM-4 series: Stable production models

See: https://open.bigmodel.cn/dev/api#models
"""

import httpx
import json
from typing import List, Dict, AsyncIterator, Optional
from .base import BaseProvider, Message, CompletionResponse, ToolCall


class ZaiProvider(BaseProvider):
    """Provider for z.ai (GLM) models using OpenAI-compatible API."""
    
    name = "z-ai"
    
    ZAI_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    
    # Current z.ai/GLM models (updated 2025)
    # See: https://open.bigmodel.cn/dev/api#models
    VALID_MODELS = {
        # GLM-5 series (latest)
        "glm-5": "GLM-5 - Latest generation flagship model",
        "glm-5-plus": "GLM-5 Plus - Enhanced capabilities",
        "glm-5-flash": "GLM-5 Flash - Fast responses",
        
        # GLM-4.7 series
        "glm-4.7": "GLM-4.7 - Improved 4.x generation",
        "glm-4.7-plus": "GLM-4.7 Plus - Enhanced 4.7",
        "glm-4.7-flash": "GLM-4.7 Flash - Fast 4.7",
        
        # GLM-4 series (stable)
        "glm-4": "GLM-4 - Standard model",
        "glm-4-plus": "GLM-4 Plus - Best 4.x quality",
        "glm-4-air": "GLM-4 Air - Balanced speed/quality",
        "glm-4-airx": "GLM-4 AirX - Extended context",
        "glm-4-long": "GLM-4 Long - Long context (128K)",
        "glm-4-flash": "GLM-4 Flash - Fastest 4.x",
        "glm-4-flashx": "GLM-4 FlashX - Extended flash",
        
        # Vision
        "glm-4v": "GLM-4V - Vision model",
        "glm-4v-plus": "GLM-4V Plus - Enhanced vision",
        
        # Legacy
        "glm-3-turbo": "GLM-3 Turbo - Legacy fast model",
    }
    
    # Default model mappings
    DEFAULT_MODEL = "glm-4-flash"
    DEFAULT_MODEL_QUICK = "glm-4-flash"
    DEFAULT_MODEL_STANDARD = "glm-4-air"
    DEFAULT_MODEL_DEEP = "glm-4-plus"
    
    def __init__(self, api_key: str = None, api_base: str = None, **kwargs):
        self.api_key = api_key
        self.api_base = api_base or self.ZAI_API_BASE
    
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """Format messages for z.ai API."""
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content,
            })
        return formatted
    
    def _format_tools(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for z.ai API."""
        if not tools:
            return []
        
        formatted_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    }
                })
        return formatted_tools
    
    def _resolve_model(self, model: str) -> str:
        """Resolve model name to valid z.ai model."""
        # Direct match
        if model in self.VALID_MODELS:
            return model
        
        # Map generic names to current best options
        model_map = {
            "auto": self.DEFAULT_MODEL,
            "quick": self.DEFAULT_MODEL_QUICK,
            "standard": self.DEFAULT_MODEL_STANDARD,
            "deep": self.DEFAULT_MODEL_DEEP,
            # Map competitor names
            "claude-3-haiku": "glm-4-flash",
            "claude-3-sonnet": "glm-4-air",
            "claude-3-opus": "glm-4-plus",
            "gpt-4": "glm-4-plus",
            "gpt-3.5-turbo": "glm-4-flash",
        }
        
        resolved = model_map.get(model.lower())
        if resolved:
            return resolved
        
        # If contains glm, try it directly
        if "glm" in model.lower():
            return model
        
        # Default fallback
        return self.DEFAULT_MODEL
    
    async def complete(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> CompletionResponse:
        """Call z.ai API."""
        
        api_model = self._resolve_model(model)
        
        payload = {
            "model": api_model,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        if tools:
            formatted_tools = self._format_tools(tools)
            if formatted_tools:
                payload["tools"] = formatted_tools
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    raise Exception(f"{response.status_code} - {error_text}")
                
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
        except httpx.TimeoutException:
            raise Exception("API timeout")
        except Exception as e:
            raise
    
    async def stream(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response from z.ai API."""
        
        api_model = self._resolve_model(model)
        
        payload = {
            "model": api_model,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"API error: {response.status_code}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except:
                            pass


class ZaiCodingProvider(ZaiProvider):
    """z.ai Coding provider - optimized for code tasks."""
    
    name = "z-ai-coding"
    
    # Coding-optimized defaults
    DEFAULT_MODEL = "glm-4-flash"  # Fast for coding iterations
    DEFAULT_MODEL_DEEP = "glm-4-plus"  # Deep thinking for complex code
    
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
    
    def _resolve_model(self, model: str) -> str:
        """Resolve model for coding tasks."""
        if model == "auto":
            return self.DEFAULT_MODEL
        return super()._resolve_model(model)
