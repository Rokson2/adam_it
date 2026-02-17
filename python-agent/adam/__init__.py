"""Adam - Personal AI Assistant"""

__version__ = "0.1.0"
__author__ = "Adam Team"

from .errors import (
    ErrorCode,
    ErrorContext,
    AdamError,
    RuntimeUnavailableError,
    RuntimeTimeoutError,
    VaultLockedError,
    FileAccessDeniedError,
    ToolNotFoundError,
    ToolExecutionError,
    LLMError,
    LLMRateLimitedError,
)

from .recovery import RecoveryManager, with_error_handling

__all__ = [
    "ErrorCode",
    "ErrorContext",
    "AdamError",
    "RuntimeUnavailableError",
    "RuntimeTimeoutError",
    "VaultLockedError",
    "FileAccessDeniedError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "LLMError",
    "LLMRateLimitedError",
    "RecoveryManager",
    "with_error_handling",
]
