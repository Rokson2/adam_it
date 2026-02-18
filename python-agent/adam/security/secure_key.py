"""
Secure API key handling with protection against:
- Accidental logging/printing
- Prompt injection (keys never go to LLM)
- Tool execution exposure
- Memory dumps (basic obfuscation)
"""

import os
import base64
import hashlib
from typing import Optional
from functools import wraps


class SecureString:
    """
    A string that cannot be accidentally printed, logged, or serialized.
    
    The actual key value is stored in an obfuscated form and only
    revealed through explicit `.get()` calls.
    """
    
    def __init__(self, value: str):
        """Create secure string with obfuscation."""
        self._obfuscated = self._obfuscate(value)
        self._length = len(value)
        # Hash for comparison without revealing value
        self._hash = hashlib.sha256(value.encode()).hexdigest()[:16]
    
    def _obfuscate(self, value: str) -> str:
        """Simple XOR obfuscation (not encryption, just prevents casual inspection)."""
        key = os.urandom(32)
        encoded = value.encode()
        result = bytes(a ^ b for a, b in zip(encoded, key * (len(encoded) // 32 + 1)))
        return base64.b64encode(key + result).decode()
    
    def _deobfuscate(self) -> str:
        """Recover the original value."""
        data = base64.b64decode(self._obfuscated.encode())
        key = data[:32]
        encoded = data[32:]
        result = bytes(a ^ b for a, b in zip(encoded, key * (len(encoded) // 32 + 1)))
        return result[:self._length].decode()
    
    def get(self) -> str:
        """
        Get the actual value. This is the ONLY way to access it.
        Use sparingly - the returned string should be passed directly
        to the API client, never stored or logged.
        """
        return self._deobfuscate()
    
    def __repr__(self) -> str:
        return f"<SecureString:***REDACTED***>"
    
    def __str__(self) -> str:
        return "***REDACTED***"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, SecureString):
            return self._hash == other._hash
        return False
    
    def __len__(self) -> int:
        return self._length
    
    def __bool__(self) -> bool:
        return self._length > 0
    
    # Prevent pickling
    def __reduce__(self):
        raise TypeError("SecureString cannot be pickled")
    
    # Prevent JSON serialization
    def __json__(self):
        return "***REDACTED***"
    
    def preview(self, chars: int = 4) -> str:
        """Show first N chars only (for debugging/verification)."""
        value = self.get()
        if len(value) <= chars:
            return "*" * len(value)
        return value[:chars] + "*" * (len(value) - chars)


class SecureKeyStore:
    """
    Central store for API keys with security protections.
    
    Keys are:
    - Never exposed to prompts sent to LLMs
    - Never passed to tool execution
    - Never logged or printed
    - Isolated from sandbox/container execution
    """
    
    _instance: Optional['SecureKeyStore'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._keys: dict[str, SecureString] = {}
            cls._instance._initialized = False
        return cls._instance
    
    def set(self, provider: str, api_key: str) -> None:
        """
        Store an API key securely.
        
        Args:
            provider: Provider name (e.g., 'anthropic', 'openai')
            api_key: The API key to store
        """
        if api_key:
            self._keys[provider.lower()] = SecureString(api_key)
    
    def get(self, provider: str) -> Optional[str]:
        """
        Get an API key. 
        
        WARNING: This returns the actual key. Only call this when
        passing directly to an API client - never log, store, or
        include in prompts.
        """
        secure_str = self._keys.get(provider.lower())
        if secure_str:
            return secure_str.get()
        return None
    
    def has(self, provider: str) -> bool:
        """Check if a key exists without revealing it."""
        return provider.lower() in self._keys
    
    def preview(self, provider: str, chars: int = 4) -> Optional[str]:
        """Get a preview of the key (first N chars only)."""
        secure_str = self._keys.get(provider.lower())
        if secure_str:
            return secure_str.preview(chars)
        return None
    
    def list_providers(self) -> list[str]:
        """List all providers that have keys configured."""
        return list(self._keys.keys())
    
    def clear(self) -> None:
        """Clear all stored keys."""
        self._keys.clear()
    
    def clear_provider(self, provider: str) -> bool:
        """Remove a specific provider's key."""
        if provider.lower() in self._keys:
            del self._keys[provider.lower()]
            return True
        return False


# Global keystore singleton
keystore = SecureKeyStore()


def redact_secrets(text: str) -> str:
    """
    Redact any API keys that might have leaked into text.
    Scans for common API key patterns and replaces them.
    """
    import re
    
    # Common API key patterns
    patterns = [
        # Anthropic: sk-ant-...
        (r'sk-ant-[a-zA-Z0-9_-]{20,}', '[ANTHROPIC_KEY_REDACTED]'),
        # OpenAI: sk-...
        (r'sk-[a-zA-Z0-9]{20,}', '[OPENAI_KEY_REDACTED]'),
        # OpenRouter: sk-or-...
        (r'sk-or-[a-zA-Z0-9_-]{20,}', '[OPENROUTER_KEY_REDACTED]'),
        # Generic Bearer tokens
        (r'Bearer\s+[a-zA-Z0-9_-]{20,}', 'Bearer [TOKEN_REDACTED]'),
        # Generic API key in URL
        (r'api[_-]?key[=:]\s*[a-zA-Z0-9_-]{10,}', 'api_key=[REDACTED]'),
    ]
    
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


def secure_log(message: str, *args) -> str:
    """
    Format a log message with automatic secret redaction.
    Use this for any logging that might accidentally contain secrets.
    """
    formatted = message % args if args else message
    return redact_secrets(formatted)


# Decorator to ensure functions don't leak secrets in exceptions
def protect_secrets(func):
    """Decorator that redacts secrets from any exception messages."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            e.args = tuple(redact_secrets(str(arg)) for arg in e.args)
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            e.args = tuple(redact_secrets(str(arg)) for arg in e.args)
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
