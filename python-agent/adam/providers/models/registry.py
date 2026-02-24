"""
Model registry with update support.

Models can be updated via:
1. Config file: ~/.adam/models.json
2. Scheduled check (weekly)
3. Manual command: adam models update
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import httpx


@dataclass
class ModelInfo:
    """Information about a model."""
    id: str
    name: str
    provider: str
    description: str = ""
    context_length: int = 4096
    supports_vision: bool = False
    supports_tools: bool = True
    deprecated: bool = False
    added_date: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModelInfo":
        return cls(**data)


# Built-in model definitions (can be overridden by config)
DEFAULT_MODELS = {
    # z.ai / GLM models
    "glm-5": ModelInfo("glm-5", "GLM-5", "z-ai", "Latest GLM-5 flagship", 128000, False, True),
    "glm-5-plus": ModelInfo("glm-5-plus", "GLM-5 Plus", "z-ai", "Enhanced GLM-5", 128000, False, True),
    "glm-5-flash": ModelInfo("glm-5-flash", "GLM-5 Flash", "z-ai", "Fast GLM-5", 32768, False, True),
    "glm-4.7": ModelInfo("glm-4.7", "GLM-4.7", "z-ai", "Improved GLM-4", 128000, False, True),
    "glm-4.7-plus": ModelInfo("glm-4.7-plus", "GLM-4.7 Plus", "z-ai", "Enhanced GLM-4.7", 128000, False, True),
    "glm-4.7-flash": ModelInfo("glm-4.7-flash", "GLM-4.7 Flash", "z-ai", "Fast GLM-4.7", 32768, False, True),
    "glm-4": ModelInfo("glm-4", "GLM-4", "z-ai", "Standard GLM-4", 128000, False, True),
    "glm-4-plus": ModelInfo("glm-4-plus", "GLM-4 Plus", "z-ai", "Best GLM-4 quality", 128000, False, True),
    "glm-4-air": ModelInfo("glm-4-air", "GLM-4 Air", "z-ai", "Balanced speed/quality", 32768, False, True),
    "glm-4-flash": ModelInfo("glm-4-flash", "GLM-4 Flash", "z-ai", "Fastest GLM-4", 32768, False, True),
    "glm-4-long": ModelInfo("glm-4-long", "GLM-4 Long", "z-ai", "Long context (128K)", 131072, False, True),
    "glm-4v": ModelInfo("glm-4v", "GLM-4V", "z-ai", "Vision model", 8192, True, True),
    
    # Anthropic models
    "claude-opus-4": ModelInfo("claude-opus-4", "Claude Opus 4", "anthropic", "Most capable", 200000, True, True),
    "claude-sonnet-4": ModelInfo("claude-sonnet-4", "Claude Sonnet 4", "anthropic", "Balanced", 200000, True, True),
    "claude-3.7-sonnet": ModelInfo("claude-3.7-sonnet", "Claude 3.7 Sonnet", "anthropic", "Improved Sonnet", 200000, True, True),
    "claude-3.5-sonnet": ModelInfo("claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", "Fast & smart", 200000, True, True),
    "claude-3-haiku": ModelInfo("claude-3-haiku", "Claude 3 Haiku", "anthropic", "Fast responses", 200000, True, True),
    
    # OpenAI models
    "gpt-4.5": ModelInfo("gpt-4.5", "GPT-4.5", "openai", "Latest GPT", 128000, True, True),
    "gpt-4o": ModelInfo("gpt-4o", "GPT-4o", "openai", "Omni model", 128000, True, True),
    "gpt-4o-mini": ModelInfo("gpt-4o-mini", "GPT-4o Mini", "openai", "Fast & cheap", 128000, True, True),
    "gpt-4-turbo": ModelInfo("gpt-4-turbo", "GPT-4 Turbo", "openai", "Fast GPT-4", 128000, True, True),
    "o1": ModelInfo("o1", "o1", "openai", "Reasoning model", 200000, False, False),
    "o1-mini": ModelInfo("o1-mini", "o1 Mini", "openai", "Fast reasoning", 128000, False, False),
    "o3-mini": ModelInfo("o3-mini", "o3 Mini", "openai", "Latest reasoning", 200000, False, False),
    
    # DeepSeek models
    "deepseek-chat": ModelInfo("deepseek-chat", "DeepSeek Chat", "deepseek", "General chat", 64000, False, True),
    "deepseek-reasoner": ModelInfo("deepseek-reasoner", "DeepSeek Reasoner", "deepseek", "Reasoning model", 64000, False, False),
    
    # Ollama (local)
    "llama3.3": ModelInfo("llama3.3", "Llama 3.3", "ollama", "Meta Llama 3.3", 128000, True, True),
    "llama3.2": ModelInfo("llama3.2", "Llama 3.2", "ollama", "Meta Llama 3.2", 128000, True, True),
    "qwen2.5": ModelInfo("qwen2.5", "Qwen 2.5", "ollama", "Alibaba Qwen", 32768, False, True),
    "mistral": ModelInfo("mistral", "Mistral", "ollama", "Mistral AI", 32768, False, True),
    "codellama": ModelInfo("codellama", "Code Llama", "ollama", "Code specialist", 16384, False, True),
}

# Provider default models
PROVIDER_DEFAULTS = {
    "z-ai": "glm-4-flash",
    "z-ai-coding": "glm-4-flash",
    "anthropic": "claude-3.5-sonnet",
    "openai": "gpt-4o",
    "deepseek": "deepseek-chat",
    "ollama": "llama3.2",
    "openrouter": "anthropic/claude-3.5-sonnet",
}

# Tier defaults (provider-agnostic)
TIER_DEFAULTS = {
    "quick": "flash",      # Suffix for quick models
    "standard": "sonnet",  # Suffix for standard models
    "deep": "opus",        # Suffix for deep models
}


class ModelRegistry:
    """Registry for LLM models with update support."""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".adam"
        self.models_file = self.config_dir / "models.json"
        self._models: Dict[str, ModelInfo] = {}
        self._last_update: Optional[datetime] = None
        self._load()
    
    def _load(self):
        """Load models from config or use defaults."""
        # Start with defaults
        self._models = DEFAULT_MODELS.copy()
        
        # Override with user config if exists
        if self.models_file.exists():
            try:
                with open(self.models_file) as f:
                    data = json.load(f)
                
                for model_id, model_data in data.get("models", {}).items():
                    self._models[model_id] = ModelInfo.from_dict(model_data)
                
                self._last_update = datetime.fromisoformat(data.get("last_update", ""))
            except Exception as e:
                print(f"Warning: Could not load models config: {e}")
    
    def _save(self):
        """Save current models to config."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            "last_update": datetime.now().isoformat(),
            "models": {k: v.to_dict() for k, v in self._models.items()}
        }
        
        with open(self.models_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def get(self, model_id: str) -> Optional[ModelInfo]:
        """Get model info by ID."""
        return self._models.get(model_id)
    
    def get_default(self, provider: str) -> str:
        """Get default model for a provider."""
        return PROVIDER_DEFAULTS.get(provider, "auto")
    
    def list_models(self, provider: str = None) -> List[ModelInfo]:
        """List all models, optionally filtered by provider."""
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return sorted(models, key=lambda m: (m.deprecated, m.provider, m.id))
    
    def list_providers(self) -> List[str]:
        """List all available providers."""
        return sorted(set(m.provider for m in self._models.values()))
    
    def add_model(self, model: ModelInfo):
        """Add or update a model."""
        self._models[model.id] = model
        self._save()
    
    def deprecate_model(self, model_id: str):
        """Mark a model as deprecated."""
        if model_id in self._models:
            self._models[model_id].deprecated = True
            self._save()
    
    def needs_update(self) -> bool:
        """Check if models should be updated (weekly)."""
        if not self._last_update:
            return True
        return datetime.now() - self._last_update > timedelta(days=7)
    
    async def check_for_updates(self) -> Dict[str, any]:
        """
        Check for new models from providers.
        
        Returns dict with:
        - new_models: List of new model IDs
        - updated: Number of models updated
        - errors: List of errors
        """
        result = {"new_models": [], "updated": 0, "errors": []}
        
        # This could be expanded to actually query provider APIs
        # For now, we just update the timestamp
        self._last_update = datetime.now()
        self._save()
        
        return result
    
    def resolve_model(self, model: str, provider: str) -> str:
        """
        Resolve a model name to a valid model ID.
        
        Args:
            model: Model name (can be 'auto', tier name, or specific model)
            provider: Provider name
        
        Returns:
            Valid model ID for the provider
        """
        # Direct match
        if model in self._models:
            return model
        
        # Provider default
        if model in ("auto", ""):
            return self.get_default(provider)
        
        # Try with provider prefix
        full_id = f"{provider}/{model}"
        if full_id in self._models:
            return full_id
        
        # Return as-is (provider will handle it)
        return model


# Global registry
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get the global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
