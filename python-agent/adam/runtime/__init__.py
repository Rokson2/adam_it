"""
Adam Runtime - gRPC communication with Go runtime.

Provides client for script execution, path validation, and profile management.
"""

from .client import RuntimeClient, ExecutionResult, PathValidation
from . import adam_pb2
from . import adam_pb2_grpc

__all__ = [
    "RuntimeClient",
    "ExecutionResult",
    "PathValidation",
    "adam_pb2",
    "adam_pb2_grpc",
]
