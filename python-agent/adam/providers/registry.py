"""
Provider registry - simplified.

Philosophy (inspired by NanoClaw):
- No hardcoded model lists
- Just map provider names to provider classes
- Let providers/SDKs handle model validation
"""

from typing import Dict, Type, Optional, List
from .base import BaseProvider

# Provider class registry
PROVIDERS: Dict[str, Type[BaseProvider]] = {}

# Lazy imports to avoid circular deps
def _load_providers():
    if PROVIDERS:
        return
    
    from .anthropic import AnthropicProvider
    from .zai import ZaiProvider, ZaiCodingProvider
    from .openrouter import OpenRouterProvider
    from .ollama import OllamaProvider
    
    PROVIDERS["anthropic"] = AnthropicProvider
    PROVIDERS["z-ai"] = ZaiProvider
    PROVIDERS["z-ai-coding"] = ZaiCodingProvider
    PROVIDERS["openrouter"] = OpenRouterProvider
    PROVIDERS["openai"] = OpenRouterProvider  # OpenRouter handles OpenAI models
    PROVIDERS["deepseek"] = OpenRouterProvider  # OpenRouter handles DeepSeek
    PROVIDERS["ollama"] = OllamaProvider


def get_provider(name: str, api_key: str = None, **kwargs) -> Optional[BaseProvider]:
    """
    Get a provider instance.
    
    Args:
        name: Provider name (e.g., "anthropic", "z-ai", "ollama")
        api_key: API key for the provider
        **kwargs: Additional provider-specific options
    
    Returns:
        Provider instance or None if not found
    """
    _load_providers()
    
    provider_class = PROVIDERS.get(name.lower())
    if not provider_class:
        return None
    
    return provider_class(api_key=api_key, **kwargs)


def list_providers() -> List[str]:
    """List available provider names."""
    _load_providers()
    return list(PROVIDERS.keys())


def load_keys_from_vault(vault) -> int:
    """
    Load API keys from vault into keystore.
    
    Returns number of keys loaded.
    """
    from adam.security import keystore
    
    # Map vault key names to provider names
    key_map = {
        "ANTHROPIC_API_KEY": "anthropic",
        "OPENAI_API_KEY": "openai",
        "OPENROUTER_API_KEY": "openrouter",
        "ZAI_API_KEY": "z-ai",
        "ZAI_CODING_API_KEY": "z-ai-coding",
        "DEEPSEEK_API_KEY": "deepseek",
        "OLLAMA_BASE_URL": "ollama",
    }
    
    loaded = 0
    for vault_key, provider_name in key_map.items():
        value = vault.get(vault_key)
        if value:
            keystore.set(provider_name, value)
            loaded += 1
    
    return loaded


# Backward compatibility
class ProviderRegistry:
    """Legacy registry class for backward compatibility."""
    
    @classmethod
    def get(cls, name: str, api_key: str = None, **kwargs) -> Optional[BaseProvider]:
        return get_provider(name, api_key, **kwargs)
    
    @classmethod
    def list_available(cls) -> List[str]:
        return list_providers()
    
    @classmethod
    def list_configured(cls) -> List[str]:
        from adam.security import keystore
        return keystore.list_providers()
