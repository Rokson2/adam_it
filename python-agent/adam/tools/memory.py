"""
Memory tools for Adam.
"""

from typing import Dict, Any, Optional

from .base import BaseTool, ToolResult


class MemoryStoreTool(BaseTool):
    """Store information in long-term memory."""

    name = "memory_store"
    description = "Store information in long-term memory for future reference. Use for facts, preferences, or important details to remember."
    parameters_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Information to remember"},
            "category": {
                "type": "string",
                "description": "Category for organization (e.g., 'preference', 'fact', 'task')",
            },
        },
        "required": ["content"],
    }

    def __init__(self, memory):
        self.memory = memory

    def execute(self, content: str, category: str = None) -> ToolResult:
        metadata = {"category": category} if category else {}
        memory_id = self.memory.store(content, metadata)

        if memory_id:
            return ToolResult(
                success=True,
                output=f"Stored in memory: {content[:100]}{'...' if len(content) > 100 else ''}",
                data={"memory_id": memory_id},
            )
        else:
            return ToolResult(success=False, output="", error="Failed to store memory")


class MemorySearchTool(BaseTool):
    """Search long-term memory."""

    name = "memory_search"
    description = "Search long-term memory for relevant information. Use to recall facts, preferences, or past interactions."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "default": 5, "description": "Maximum results to return"},
        },
        "required": ["query"],
    }

    def __init__(self, memory):
        self.memory = memory

    def execute(self, query: str, limit: int = 5) -> ToolResult:
        results = self.memory.search(query, limit=limit)

        if results:
            output_lines = [f"Found {len(results)} memories:"]
            for i, item in enumerate(results, 1):
                output_lines.append(f"\n{i}. {item.content}")
                if item.score > 0:
                    output_lines.append(f"   (relevance: {item.score:.2f})")

            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                data={
                    "count": len(results),
                    "results": [{"content": r.content, "score": r.score} for r in results],
                },
            )
        else:
            return ToolResult(
                success=True, output="No memories found matching query.", data={"count": 0}
            )


class MemoryListTool(BaseTool):
    """List all memories."""

    name = "memory_list"
    description = "List all stored memories. Use to see what information has been remembered."
    parameters_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 20, "description": "Maximum memories to list"}
        },
        "required": [],
    }

    def __init__(self, memory):
        self.memory = memory

    def execute(self, limit: int = 20) -> ToolResult:
        results = self.memory.get_all()

        if results:
            output_lines = [f"Total memories: {len(results)}"]
            for i, item in enumerate(results[:limit], 1):
                output_lines.append(
                    f"\n{i}. {item.content[:100]}{'...' if len(item.content) > 100 else ''}"
                )

            if len(results) > limit:
                output_lines.append(f"\n... and {len(results) - limit} more")

            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                data={"total": len(results), "shown": min(len(results), limit)},
            )
        else:
            return ToolResult(success=True, output="No memories stored yet.", data={"total": 0})
