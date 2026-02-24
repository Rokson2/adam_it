"""
Ollama provider - simplified.

Ollama runs models locally. Model selection delegated to Ollama.
"""

from typing import List, Dict
import httpx
import json

from .base import BaseProvider, Message, CompletionResponse, ToolCall


class OllamaProvider(BaseProvider):
    """Provider for Ollama (local models)."""
    
    name = "ollama"
    default_model = "llama3.2"
    api_base = "http://localhost:11434"
    
    def __init__(self, api_base: str = None, **kwargs):
        if api_base:
            self.api_base = api_base
    
    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        return [{"role": m.role, "content": m.content} for m in messages]
    
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
            "stream": False,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/api/chat",
                json=payload,
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code} - {response.text}")
            
            data = response.json()
        
        message = data.get("message", {})
        content = message.get("content", "")
        
        return CompletionResponse(
            content=content,
            tool_calls=[],  # Ollama tool support varies by model
            finish_reason="stop",
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
            model=data.get("model", resolved_model)
        )
    
    def supports_tools(self) -> bool:
        return False  # Varies by model
