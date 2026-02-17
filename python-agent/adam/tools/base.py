"""
Base tool interface and registry for Adam.

Tools are the actions the agent can take. Each tool implements
the BaseTool interface and registers with the ToolRegistry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json


@dataclass
class ToolResult:
    """Result of tool execution."""

    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """Base class for all tools."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters_schema,
        }

    def validate_args(self, kwargs: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate arguments against schema.

        Returns:
            Tuple of (is_valid, error_message)
        """
        required = self.parameters_schema.get("required", [])
        properties = self.parameters_schema.get("properties", {})

        # Check required parameters
        for req in required:
            if req not in kwargs:
                return False, f"Missing required parameter: {req}"

        # Check parameter types (basic validation)
        for key, value in kwargs.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type:
                    if not self._check_type(value, expected_type):
                        return False, f"Parameter '{key}' should be {expected_type}"

        return True, ""

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, skip validation
        return isinstance(value, expected)


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI format."""
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in Anthropic format."""
        return [tool.to_anthropic_tool() for tool in self._tools.values()]

    def execute(self, name: str, kwargs: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool by name with given arguments.

        Handles validation and error wrapping.
        """
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Unknown tool: {name}")

        # Validate arguments
        is_valid, error = tool.validate_args(kwargs)
        if not is_valid:
            return ToolResult(success=False, output="", error=error)

        # Execute tool
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Tool execution failed: {str(e)}")

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: BaseTool) -> None:
    """Register a tool with the global registry."""
    get_registry().register(tool)
