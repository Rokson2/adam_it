"""
Python gRPC client for Adam Runtime.

Provides a high-level interface to communicate with the Go runtime
for script execution, path validation, and profile management.
"""

import time
import grpc
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from . import adam_pb2
from . import adam_pb2_grpc


@dataclass
class ExecutionResult:
    """Result of script execution."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


@dataclass
class PathValidation:
    """Result of path validation."""

    allowed: bool
    resolved_path: str
    denial_reason: str


class RuntimeClient:
    """
    Client for communicating with Adam Runtime via gRPC.

    Uses Unix domain sockets for local communication.
    """

    DEFAULT_SOCKET = "/tmp/adam-runtime.sock"

    def __init__(self, socket_path: str = None):
        """
        Initialize runtime client.

        Args:
            socket_path: Path to Unix socket. Defaults to /tmp/adam-runtime.sock
        """
        self.socket_path = socket_path or self.DEFAULT_SOCKET
        self._channel: Optional[grpc.Channel] = None
        self._stub: Optional[adam_pb2_grpc.RuntimeServiceStub] = None

    def _get_channel(self) -> grpc.Channel:
        """Get or create gRPC channel."""
        if self._channel is None:
            self._channel = grpc.insecure_channel(f"unix://{self.socket_path}")
        return self._channel

    def _get_stub(self) -> adam_pb2_grpc.RuntimeServiceStub:
        """Get or create gRPC stub."""
        if self._stub is None:
            self._stub = adam_pb2_grpc.RuntimeServiceStub(self._get_channel())
        return self._stub

    def execute_script(
        self,
        script_path: str,
        args: List[str] = None,
        env: Dict[str, str] = None,
        timeout_seconds: int = 300,
    ) -> ExecutionResult:
        """
        Execute a script in a sandboxed container.

        Args:
            script_path: Path to the script to execute
            args: List of arguments to pass to the script
            env: Environment variables for the script
            timeout_seconds: Maximum execution time

        Returns:
            ExecutionResult with exit code, stdout, stderr, and timeout flag
        """
        request = adam_pb2.ScriptRequest(
            script_path=script_path,
            args=args or [],
            env=env or {},
            timeout_seconds=timeout_seconds,
        )

        response = self._get_stub().ExecuteScript(request)

        return ExecutionResult(
            exit_code=response.exit_code,
            stdout=response.stdout,
            stderr=response.stderr,
            timed_out=response.timed_out,
        )

    def validate_path(self, path: str, operation: str) -> PathValidation:
        """
        Validate if a path can be accessed for a given operation.

        Args:
            path: Path to validate
            operation: One of "read", "write", "execute"

        Returns:
            PathValidation with allowed flag, resolved path, and denial reason
        """
        request = adam_pb2.PathRequest(
            path=path,
            operation=operation,
        )

        response = self._get_stub().ValidatePath(request)

        return PathValidation(
            allowed=response.allowed,
            resolved_path=response.resolved_path,
            denial_reason=response.denial_reason,
        )

    def get_status(self) -> Dict[str, any]:
        """
        Get runtime status.

        Returns:
            Dictionary with runtime_healthy, active_containers, current_profile
        """
        request = adam_pb2.StatusRequest()
        response = self._get_stub().GetStatus(request)

        return {
            "runtime_healthy": response.runtime_healthy,
            "active_containers": response.active_containers,
            "current_profile": response.current_profile,
        }

    def get_profile(self) -> str:
        """
        Get the current profile name.

        Returns:
            Current profile name
        """
        request = adam_pb2.ProfileRequest()
        response = self._get_stub().GetProfile(request)
        return response.name

    def set_profile(self, profile_name: str) -> bool:
        """
        Set the active security profile.

        Args:
            profile_name: Name of profile to activate

        Returns:
            True if successful
        """
        request = adam_pb2.SetProfileRequest(profile_name=profile_name)
        response = self._get_stub().SetProfile(request)
        return response.name == profile_name

    def is_available(self, retries: int = 3, delay: float = 0.5) -> bool:
        """
        Check if the runtime is available.

        Args:
            retries: Number of retries before giving up
            delay: Delay between retries in seconds

        Returns:
            True if runtime is running and responding
        """
        for attempt in range(retries):
            try:
                self.get_status()
                return True
            except Exception:
                if attempt < retries - 1:
                    time.sleep(delay)
        return False

    def close(self):
        """Close the gRPC channel."""
        if self._channel:
            self._channel.close()
            self._channel = None
            self._stub = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
