"""
Provider registry for managing LLM providers.
"""

from typing import Dict, Type, Optional, List
from .base import BaseProvider, Message, CompletionResponse
from .anthropic import AnthropicProvider
from .openrouter import OpenRouterProvider
from .ollama import OllamaProvider


class ProviderRegistry:
    """Registry for LLM providers."""

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
    def get(cls, name: str, **kwargs) -> Optional[BaseProvider]:
        """
        Get or create a provider instance.

        Args:
            name: Provider name
            **kwargs: Provider-specific configuration

        Returns:
            Provider instance or None if not found
        """
        cache_key = f"{name}:{hash(frozenset(kwargs.items()))}"

        if cache_key not in cls._instances:
            provider_class = cls._providers.get(name)
            if not provider_class:
                return None
            cls._instances[cache_key] = provider_class(**kwargs)

        return cls._instances[cache_key]

    @classmethod
    def list_available(cls) -> List[str]:
        """List available provider names."""
        return list(cls._providers.keys())

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached instances."""
        cls._instances.clear()


def get_provider(name: str, **kwargs) -> Optional[BaseProvider]:
    """Convenience function to get a provider."""
    return ProviderRegistry.get(name, **kwargs)
