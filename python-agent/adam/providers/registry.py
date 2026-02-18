"""
Provider registry for managing LLM providers.
Uses secure keystore for API keys - keys are NEVER exposed to:
- LLM prompts
- Tool execution  
- Logs or debug output
"""

from typing import Dict, Type, Optional, List
from .base import BaseProvider, Message, CompletionResponse
from .anthropic import AnthropicProvider
from .openrouter import OpenRouterProvider
from .ollama import OllamaProvider
from adam.security import keystore


class ProviderRegistry:
    """Registry for LLM providers with secure key handling."""

    _providers: Dict[str, Type[BaseProvider]] = {
        "anthropic": AnthropicProvider,
        "openrouter": OpenRouterProvider,
        "openai": OpenRouterProvider,  # OpenRouter can handle OpenAI models
        "ollama": OllamaProvider,
    }

    _instances: Dict[str, BaseProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """Register a provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def get(cls, name: str, api_key: str = None, **kwargs) -> Optional[BaseProvider]:
        """
        Get or create a provider instance.
        
        API keys are retrieved from the secure keystore, NOT from parameters.
        The api_key parameter is only used as a fallback for explicit overrides.
        
        Args:
            name: Provider name
            api_key: Optional explicit key (not recommended - use keystore)
            **kwargs: Provider-specific configuration

        Returns:
            Provider instance or None if not found
        """
        provider_name = name.lower()
        
        # Check if we need to create a new instance
        # Cache key doesn't include API key (that's managed separately)
        cache_key = f"{provider_name}:{hash(frozenset(kwargs.items()))}"

        if cache_key not in cls._instances:
            provider_class = cls._providers.get(provider_name)
            if not provider_class:
                return None
            
            # Get API key from secure keystore (preferred) or parameter (fallback)
            # Key is retrieved securely and passed directly to provider
            resolved_key = api_key or keystore.get(provider_name)
            
            # Create provider - key is passed directly, never logged
            cls._instances[cache_key] = provider_class(api_key=resolved_key, **kwargs)

        return cls._instances[cache_key]

    @classmethod
    def list_available(cls) -> List[str]:
        """List available provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def list_configured(cls) -> List[str]:
        """List providers that have API keys configured."""
        configured = []
        for provider in cls._providers:
            if keystore.has(provider):
                configured.append(provider)
        return configured
    
    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached instances."""
        cls._instances.clear()

    @classmethod
    def get_key_preview(cls, provider: str, chars: int = 4) -> Optional[str]:
        """Get a preview of the configured key (for verification)."""
        return keystore.preview(provider, chars)


def get_provider(name: str, api_key: str = None, **kwargs) -> Optional[BaseProvider]:
    """Convenience function to get a provider."""
    return ProviderRegistry.get(name, api_key=api_key, **kwargs)


def load_keys_from_vault(vault) -> int:
    """
    Load all API keys from vault into secure keystore.
    This should be called after vault is unlocked.
    
    Returns number of keys loaded.
    """
    key_mappings = {
        "ANTHROPIC_API_KEY": "anthropic",
        "OPENAI_API_KEY": "openai", 
        "OPENROUTER_API_KEY": "openrouter",
        "DEEPSEEK_API_KEY": "deepseek",
        "ZAI_API_KEY": "z-ai",
        "ZAI_CODING_API_KEY": "z-ai-coding",
        "OLLAMA_BASE_URL": "ollama",
    }
    
    loaded = 0
    for vault_key, provider_name in key_mappings.items():
        value = vault.get(vault_key)
        if value:
            keystore.set(provider_name, value)
            loaded += 1
    
    return loaded
