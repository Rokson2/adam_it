"""
Error types and handling for Adam.

Provides structured error handling with error codes and recovery hints.
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class ErrorCode(Enum):
    """Error codes for Adam."""

    # Runtime errors (E001-E099)
    RUNTIME_UNAVAILABLE = "E001"
    RUNTIME_TIMEOUT = "E002"
    RUNTIME_ERROR = "E003"

    # Vault errors (E100-E199)
    VAULT_LOCKED = "E100"
    VAULT_ERROR = "E101"
    VAULT_CORRUPTED = "E102"

    # File access errors (E200-E299)
    FILE_ACCESS_DENIED = "E200"
    FILE_NOT_FOUND = "E201"
    FILE_READ_ERROR = "E202"
    FILE_WRITE_ERROR = "E203"

    # Tool errors (E300-E399)
    TOOL_NOT_FOUND = "E300"
    TOOL_EXECUTION_FAILED = "E301"
    TOOL_TIMEOUT = "E302"
    TOOL_INVALID_ARGS = "E303"

    # LLM errors (E400-E499)
    LLM_ERROR = "E400"
    LLM_RATE_LIMITED = "E401"
    LLM_CONTEXT_TOO_LONG = "E402"
    LLM_INVALID_RESPONSE = "E403"

    # Network errors (E500-E599)
    NETWORK_ERROR = "E500"
    NETWORK_TIMEOUT = "E501"

    # Configuration errors (E600-E699)
    CONFIG_ERROR = "E600"
    CONFIG_MISSING = "E601"
    CONFIG_INVALID = "E602"

    # General errors (E900-E999)
    INVALID_INPUT = "E900"
    UNKNOWN_ERROR = "E999"


@dataclass
class ErrorContext:
    """Context for an error."""

    component: str = ""
    operation: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class AdamError(Exception):
    """
    Base exception for Adam.

    All Adam exceptions inherit from this class and provide:
    - Error code for categorization
    - User-friendly message
    - Recovery hints
    - Whether the error is recoverable
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        recoverable: bool = True,
        context: ErrorContext = None,
        recovery_hint: str = None,
    ):
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.context = context
        self.recovery_hint = recovery_hint or self._default_recovery_hint()
        super().__init__(f"[{code.value}] {message}")

    def _default_recovery_hint(self) -> str:
        """Get default recovery hint based on error code."""
        hints = {
            ErrorCode.RUNTIME_UNAVAILABLE: "Start the runtime with: adam-runtime",
            ErrorCode.VAULT_LOCKED: "Unlock the vault with: adam vault unlock",
            ErrorCode.FILE_ACCESS_DENIED: "Check if the path is in the allowed directories for your profile",
            ErrorCode.TOOL_NOT_FOUND: "The requested tool is not available",
            ErrorCode.LLM_ERROR: "Check your API key and network connection",
            ErrorCode.LLM_RATE_LIMITED: "Wait a moment and try again",
            ErrorCode.NETWORK_ERROR: "Check your internet connection",
        }
        return hints.get(self.code, "Try again or check the documentation")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "code": self.code.value,
            "message": self.message,
            "recoverable": self.recoverable,
            "recovery_hint": self.recovery_hint,
            "context": {
                "component": self.context.component if self.context else "",
                "operation": self.context.operation if self.context else "",
                "details": self.context.details if self.context else {},
            },
        }

    def user_message(self) -> str:
        """Get user-friendly error message."""
        parts = [self.message]
        if self.recovery_hint:
            parts.append(f"Hint: {self.recovery_hint}")
        return " | ".join(parts)


# Specific error classes


class RuntimeUnavailableError(AdamError):
    """Runtime is not available."""

    def __init__(self, detail: str = ""):
        super().__init__(
            code=ErrorCode.RUNTIME_UNAVAILABLE,
            message=f"Adam Runtime is not available. {detail}".strip(),
            recoverable=True,
        )


class RuntimeTimeoutError(AdamError):
    """Runtime operation timed out."""

    def __init__(self, operation: str, timeout: int):
        super().__init__(
            code=ErrorCode.RUNTIME_TIMEOUT,
            message=f"Operation '{operation}' timed out after {timeout}s",
            recoverable=True,
        )


class VaultLockedError(AdamError):
    """Vault is locked."""

    def __init__(self):
        super().__init__(
            code=ErrorCode.VAULT_LOCKED,
            message="Vault is locked",
            recoverable=True,
            recovery_hint="Run 'adam vault unlock' to access secrets",
        )


class FileAccessDeniedError(AdamError):
    """File access denied by security profile."""

    def __init__(self, path: str, reason: str):
        super().__init__(
            code=ErrorCode.FILE_ACCESS_DENIED,
            message=f"Access denied to '{path}': {reason}",
            recoverable=False,
        )


class ToolNotFoundError(AdamError):
    """Tool not found."""

    def __init__(self, tool_name: str):
        super().__init__(
            code=ErrorCode.TOOL_NOT_FOUND,
            message=f"Tool not found: {tool_name}",
            recoverable=False,
        )


class ToolExecutionError(AdamError):
    """Tool execution failed."""

    def __init__(self, tool_name: str, error: str):
        super().__init__(
            code=ErrorCode.TOOL_EXECUTION_FAILED,
            message=f"Tool '{tool_name}' failed: {error}",
            recoverable=True,
        )


class LLMError(AdamError):
    """LLM provider error."""

    def __init__(self, provider: str, error: str):
        super().__init__(
            code=ErrorCode.LLM_ERROR,
            message=f"LLM error ({provider}): {error}",
            recoverable=True,
            recovery_hint="Check your API key and try again",
        )


class LLMRateLimitedError(AdamError):
    """LLM rate limited."""

    def __init__(self, provider: str):
        super().__init__(
            code=ErrorCode.LLM_RATE_LIMITED,
            message=f"Rate limited by {provider}",
            recoverable=True,
            recovery_hint="Wait a moment before retrying",
        )
