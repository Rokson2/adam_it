"""
Model registry with update support.

Models confirmed from official sources:
- Anthropic: docs.anthropic.com (Feb 2025)
- OpenAI: github.com/openai/openai-python (Feb 2025)
- z.ai/GLM: NEEDS CONFIRMATION - user should verify model IDs
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
    context_length: int = 200000
    supports_vision: bool = False
    supports_tools: bool = True
    deprecated: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModelInfo":
        return cls(**data)


# =============================================================================
# CONFIRMED MODELS (from official sources)
# =============================================================================

DEFAULT_MODELS = {
    # -------------------------------------------------------------------------
    # ANTHROPIC CLAUDE (confirmed from docs.anthropic.com Feb 2025)
    # -------------------------------------------------------------------------
    "claude-opus-4-6": ModelInfo(
        "claude-opus-4-6", "Claude Opus 4.6", "anthropic",
        "Most intelligent model for agents and coding", 200000, True, True
    ),
    "claude-sonnet-4-6": ModelInfo(
        "claude-sonnet-4-6", "Claude Sonnet 4.6", "anthropic",
        "Best combination of speed and intelligence", 200000, True, True
    ),
    "claude-haiku-4-5": ModelInfo(
        "claude-haiku-4-5-20251001", "Claude Haiku 4.5", "anthropic",
        "Fastest model with near-frontier intelligence", 200000, True, True
    ),
    "claude-sonnet-4-5": ModelInfo(
        "claude-sonnet-4-5-20250929", "Claude Sonnet 4.5", "anthropic",
        "Legacy - consider migrating to 4.6", 200000, True, True
    ),
    "claude-opus-4-5": ModelInfo(
        "claude-opus-4-5-20251101", "Claude Opus 4.5", "anthropic",
        "Legacy - consider migrating to 4.6", 200000, True, True
    ),
    "claude-sonnet-4": ModelInfo(
        "claude-sonnet-4-20250514", "Claude Sonnet 4", "anthropic",
        "Legacy", 200000, True, True
    ),
    "claude-opus-4": ModelInfo(
        "claude-opus-4-20250514", "Claude Opus 4", "anthropic",
        "Legacy", 200000, True, True
    ),
    "claude-3-5-sonnet": ModelInfo(
        "claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", "anthropic",
        "Legacy - fast and smart", 200000, True, True
    ),
    "claude-3-haiku": ModelInfo(
        "claude-3-haiku-20240307", "Claude 3 Haiku", "anthropic",
        "DEPRECATED - retiring April 2026", 200000, True, True, deprecated=True
    ),
    
    # -------------------------------------------------------------------------
    # OPENAI (confirmed from openai-python source Feb 2025)
    # -------------------------------------------------------------------------
    "gpt-5.2": ModelInfo(
        "gpt-5.2", "GPT-5.2", "openai",
        "Latest GPT-5.2 model", 200000, True, True
    ),
    "gpt-5.2-pro": ModelInfo(
        "gpt-5.2-pro", "GPT-5.2 Pro", "openai",
        "GPT-5.2 Pro - enhanced capabilities", 200000, True, True
    ),
    "gpt-5.1": ModelInfo(
        "gpt-5.1", "GPT-5.1", "openai",
        "GPT-5.1 series", 200000, True, True
    ),
    "gpt-5.1-mini": ModelInfo(
        "gpt-5.1-mini", "GPT-5.1 Mini", "openai",
        "Fast GPT-5.1", 128000, True, True
    ),
    "gpt-5": ModelInfo(
        "gpt-5", "GPT-5", "openai",
        "GPT-5 base model", 128000, True, True
    ),
    "gpt-5-mini": ModelInfo(
        "gpt-5-mini", "GPT-5 Mini", "openai",
        "Fast and efficient GPT-5", 128000, True, True
    ),
    "gpt-4.1": ModelInfo(
        "gpt-4.1", "GPT-4.1", "openai",
        "GPT-4.1 - improved GPT-4", 128000, True, True
    ),
    "gpt-4.1-mini": ModelInfo(
        "gpt-4.1-mini", "GPT-4.1 Mini", "openai",
        "Fast GPT-4.1", 128000, True, True
    ),
    "gpt-4o": ModelInfo(
        "gpt-4o", "GPT-4o", "openai",
        "Omni model - multimodal", 128000, True, True
    ),
    "gpt-4o-mini": ModelInfo(
        "gpt-4o-mini", "GPT-4o Mini", "openai",
        "Fast and affordable", 128000, True, True
    ),
    "gpt-4-turbo": ModelInfo(
        "gpt-4-turbo", "GPT-4 Turbo", "openai",
        "Fast GPT-4", 128000, True, True
    ),
    "gpt-4": ModelInfo(
        "gpt-4", "GPT-4", "openai",
        "GPT-4 base", 8192, False, True
    ),
    "o3": ModelInfo(
        "o3", "o3", "openai",
        "Reasoning model", 200000, False, False
    ),
    "o3-mini": ModelInfo(
        "o3-mini", "o3 Mini", "openai",
        "Fast reasoning", 200000, False, False
    ),
    "o1": ModelInfo(
        "o1", "o1", "openai",
        "Reasoning model", 200000, False, False
    ),
    "o1-mini": ModelInfo(
        "o1-mini", "o1 Mini", "openai",
        "Fast reasoning", 128000, False, False
    ),
    
    # -------------------------------------------------------------------------
    # z.ai / GLM (NEEDS CONFIRMATION - verify model IDs)
    # Source: User mentioned GLM-4.7 and GLM-5 but exact IDs unknown
    # -------------------------------------------------------------------------
    "glm-4-plus": ModelInfo(
        "glm-4-plus", "GLM-4 Plus", "z-ai",
        "Best GLM-4 quality", 128000, False, True
    ),
    "glm-4-air": ModelInfo(
        "glm-4-air", "GLM-4 Air", "z-ai",
        "Balanced speed/quality", 128000, False, True
    ),
    "glm-4-flash": ModelInfo(
        "glm-4-flash", "GLM-4 Flash", "z-ai",
        "Fastest GLM-4", 128000, False, True
    ),
    "glm-4-long": ModelInfo(
        "glm-4-long", "GLM-4 Long", "z-ai",
        "Long context (128K)", 131072, False, True
    ),
    "glm-4v": ModelInfo(
        "glm-4v", "GLM-4V", "z-ai",
        "Vision model", 8192, True, True
    ),
    # NOTE: User mentioned glm-4.7 and glm-5 but exact model IDs need confirmation
    # Add them to ~/.adam/models.json when confirmed
    
    # -------------------------------------------------------------------------
    # DEEPSEEK
    # -------------------------------------------------------------------------
    "deepseek-chat": ModelInfo(
        "deepseek-chat", "DeepSeek Chat", "deepseek",
        "General chat model", 64000, False, True
    ),
    "deepseek-reasoner": ModelInfo(
        "deepseek-reasoner", "DeepSeek Reasoner", "deepseek",
        "Reasoning model", 64000, False, False
    ),
    
    # -------------------------------------------------------------------------
    # OLLAMA (local models)
    # -------------------------------------------------------------------------
    "llama3.3": ModelInfo(
        "llama3.3", "Llama 3.3", "ollama",
        "Meta Llama 3.3", 128000, True, True
    ),
    "llama3.2": ModelInfo(
        "llama3.2", "Llama 3.2", "ollama",
        "Meta Llama 3.2", 128000, True, True
    ),
    "qwen2.5": ModelInfo(
        "qwen2.5", "Qwen 2.5", "ollama",
        "Alibaba Qwen 2.5", 32768, False, True
    ),
    "mistral": ModelInfo(
        "mistral", "Mistral", "ollama",
        "Mistral AI", 32768, False, True
    ),
    "codellama": ModelInfo(
        "codellama", "Code Llama", "ollama",
        "Code specialist", 16384, False, True
    ),
}

# Provider default models
PROVIDER_DEFAULTS = {
    "z-ai": "glm-4-flash",
    "z-ai-coding": "glm-4-flash",
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "deepseek": "deepseek-chat",
    "ollama": "llama3.2",
    "openrouter": "anthropic/claude-sonnet-4-6",
}


class ModelRegistry:
    """Registry for LLM models."""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".adam"
        self.models_file = self.config_dir / "models.json"
        self._models: Dict[str, ModelInfo] = {}
        self._load()
    
    def _load(self):
        """Load models from config or use defaults."""
        self._models = DEFAULT_MODELS.copy()
        
        if self.models_file.exists():
            try:
                with open(self.models_file) as f:
                    data = json.load(f)
                for model_id, model_data in data.get("models", {}).items():
                    self._models[model_id] = ModelInfo.from_dict(model_data)
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
        return self._models.get(model_id)
    
    def get_default(self, provider: str) -> str:
        return PROVIDER_DEFAULTS.get(provider, "auto")
    
    def list_models(self, provider: str = None) -> List[ModelInfo]:
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return sorted(models, key=lambda m: (m.deprecated, m.provider, m.id))
    
    def list_providers(self) -> List[str]:
        return sorted(set(m.provider for m in self._models.values()))
    
    def add_model(self, model: ModelInfo):
        self._models[model.id] = model
        self._save()
    
    def resolve_model(self, model: str, provider: str) -> str:
        if model in self._models:
            return model
        if model in ("auto", ""):
            return self.get_default(provider)
        return model


_registry: Optional["ModelRegistry"] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
