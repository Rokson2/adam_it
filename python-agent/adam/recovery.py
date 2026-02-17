"""
Recovery mechanisms for Adam.

Provides automatic retry and recovery strategies.
"""

import asyncio
from typing import Callable, TypeVar, Optional
from functools import wraps
import random

from .errors import AdamError, ErrorCode

T = TypeVar("T")


class RecoveryManager:
    """
    Manages error recovery with retry strategies.

    Strategies:
    - Immediate retry for transient errors
    - Exponential backoff for rate limits
    - Fallback for recoverable errors
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def with_retry(
        self,
        operation: Callable[[], T],
        retry_on: tuple = (AdamError,),
        exclude_on: tuple = (),
    ) -> T:
        """
        Execute operation with automatic retry.

        Args:
            operation: Async function to execute
            retry_on: Exception types to retry on
            exclude_on: Exception types to never retry

        Returns:
            Result of operation

        Raises:
            Last exception if all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await operation()
                return result
            except exclude_on:
                raise
            except retry_on as e:
                last_error = e

                # Check if error is recoverable
                if isinstance(e, AdamError) and not e.recoverable:
                    raise

                # Last attempt, don't wait
                if attempt == self.max_retries:
                    raise

                # Calculate delay with exponential backoff + jitter
                delay = min(self.base_delay * (2**attempt) + random.uniform(0, 1), self.max_delay)

                await asyncio.sleep(delay)

        raise last_error

    async def with_fallback(
        self,
        primary: Callable[[], T],
        fallback: Callable[[], T],
    ) -> T:
        """
        Execute with fallback on failure.

        Args:
            primary: Primary operation
            fallback: Fallback operation if primary fails

        Returns:
            Result from primary or fallback
        """
        try:
            return await primary()
        except Exception:
            return await fallback()

    def should_retry(self, error: Exception) -> bool:
        """Determine if an error should be retried."""
        if isinstance(error, AdamError):
            if not error.recoverable:
                return False

            # Specific error codes that should be retried
            retry_codes = {
                ErrorCode.LLM_ERROR,
                ErrorCode.RUNTIME_TIMEOUT,
                ErrorCode.LLM_RATE_LIMITED,
                ErrorCode.NETWORK_TIMEOUT,
                ErrorCode.NETWORK_ERROR,
            }
            return error.code in retry_codes

        # Unknown errors, don't retry
        return False


def with_error_handling(func: Callable) -> Callable:
    """
    Decorator to add error handling to functions.

    Catches Adam errors and logs them appropriately.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AdamError as e:
            # Log and re-raise with context
            print(f"[Adam Error {e.code.value}] {e.message}")
            if e.recovery_hint:
                print(f"  Hint: {e.recovery_hint}")
            raise
        except Exception as e:
            # Wrap unknown errors
            print(f"[Unexpected Error] {str(e)}")
            raise

    return wrapper
