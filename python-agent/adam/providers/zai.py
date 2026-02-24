"""z.ai (GLM) provider - OpenAI-compatible API."""

import httpx
import json
from typing import List, Dict, AsyncIterator, Optional
from .base import BaseProvider, Message, CompletionResponse, ToolCall


class ZaiProvider(BaseProvider):
    """Provider for z.ai (GLM) models using OpenAI-compatible API."""
    
    name = "z-ai"
    
    ZAI_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    
    def __init__(self, api_key: str = None, api_base: str = None, **kwargs):
        self.api_key = api_key
        self.api_base = api_base or self.ZAI_API_BASE
        self.client = httpx.AsyncClient(timeout=120.0)
    
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
        """Format tools for z.ai API - requires type field."""
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
    
    async def complete(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> CompletionResponse:
        """Call z.ai API."""
        
        model_map = {
            "auto": "glm-4-flash",
            "glm-4": "glm-4",
            "glm-4-flash": "glm-4-flash",
            "glm-4-plus": "glm-4-plus",
            "glm-4-air": "glm-4-air",
        }
        
        api_model = model_map.get(model, model)
        
        payload = {
            "model": api_model,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        # Only add tools if we have valid ones
        if tools:
            formatted_tools = self._format_tools(tools)
            if formatted_tools:
                payload["tools"] = formatted_tools
        
        try:
            response = await self.client.post(
                f"{self.api_base}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            
            if response.status_code != 200:
                error_text = response.text
                raise Exception(f"z.ai API error: {response.status_code} - {error_text}")
            
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
            raise Exception("z.ai API timeout")
        except Exception as e:
            raise Exception(f"z.ai API error: {str(e)}")
    
    async def stream(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response from z.ai API."""
        
        model_map = {
            "auto": "glm-4-flash",
            "glm-4": "glm-4",
            "glm-4-flash": "glm-4-flash",
        }
        
        api_model = model_map.get(model, model)
        
        payload = {
            "model": api_model,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }
        
        async with self.client.stream(
            "POST",
            f"{self.api_base}/chat/completions",
            headers=self._get_headers(),
            json=payload,
        ) as response:
            if response.status_code != 200:
                raise Exception(f"z.ai API error: {response.status_code}")
            
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
    """z.ai Coding provider - same API, optimized for coding."""
    
    name = "z-ai-coding"
    
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
    
    async def complete(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict] = None,
        **kwargs,
    ) -> CompletionResponse:
        if model == "auto":
            model = "glm-4-flash"
        return await super().complete(messages, model, tools, **kwargs)
