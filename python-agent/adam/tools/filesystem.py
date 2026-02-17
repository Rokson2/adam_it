"""
Filesystem tools for Adam.

Provides secure file operations with path validation through the runtime.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import os

from .base import BaseTool, ToolResult
from ..runtime import RuntimeClient


class FileReadTool(BaseTool):
    """Read the contents of a file from an allowed directory."""

    name = "file_read"
    description = "Read the contents of a file from an allowed directory. Use this to examine files, code, or documents."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read. Can be absolute or relative to home directory.",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (0-based). Use for large files.",
                "default": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read.",
                "default": 2000,
            },
        },
        "required": ["path"],
    }

    def __init__(self, runtime_client: RuntimeClient):
        self.runtime = runtime_client

    def execute(self, path: str, offset: int = 0, limit: int = 2000) -> ToolResult:
        validation = self.runtime.validate_path(path, "read")
        if not validation.allowed:
            return ToolResult(
                success=False, output="", error=f"Access denied: {validation.denial_reason}"
            )

        try:
            file_path = Path(validation.resolved_path)
            if not file_path.exists():
                return ToolResult(success=False, output="", error=f"File not found: {path}")

            if not file_path.is_file():
                return ToolResult(success=False, output="", error=f"Not a file: {path}")

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            start = max(0, offset)
            end = min(offset + limit, len(lines))
            selected = lines[start:end]

            output_lines = []
            for i, line in enumerate(selected, start=offset + 1):
                line_content = line.rstrip("\n\r")
                output_lines.append(f"{i:6}\t{line_content}")

            content = "\n".join(output_lines)

            return ToolResult(
                success=True,
                output=content,
                data={
                    "total_lines": len(lines),
                    "returned_lines": len(selected),
                    "offset": offset,
                    "limit": limit,
                },
            )
        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error reading file: {str(e)}")


class FileWriteTool(BaseTool):
    """Write content to a file in an allowed directory."""

    name = "file_write"
    description = (
        "Write content to a file in an allowed directory. Creates the file if it doesn't exist."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to write."},
            "content": {"type": "string", "description": "Content to write to the file."},
            "mode": {
                "type": "string",
                "enum": ["write", "append"],
                "default": "write",
                "description": "Write mode: 'write' overwrites, 'append' adds to end.",
            },
        },
        "required": ["path", "content"],
    }

    def __init__(self, runtime_client: RuntimeClient):
        self.runtime = runtime_client

    def execute(self, path: str, content: str, mode: str = "write") -> ToolResult:
        validation = self.runtime.validate_path(path, "write")
        if not validation.allowed:
            return ToolResult(
                success=False, output="", error=f"Access denied: {validation.denial_reason}"
            )

        try:
            file_path = Path(validation.resolved_path)

            file_path.parent.mkdir(parents=True, exist_ok=True)

            write_mode = "w" if mode == "write" else "a"
            with open(file_path, write_mode, encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
                data={
                    "bytes_written": len(content.encode("utf-8")),
                    "chars_written": len(content),
                    "mode": mode,
                },
            )
        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error writing file: {str(e)}")


class FileListTool(BaseTool):
    """List files in a directory."""

    name = "file_list"
    description = (
        "List files and directories in a given path. Returns names sorted by modification time."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to list."},
            "pattern": {
                "type": "string",
                "default": "*",
                "description": "Glob pattern to filter files (e.g., '*.py', '*.txt').",
            },
            "show_hidden": {
                "type": "boolean",
                "default": False,
                "description": "Include hidden files (starting with .).",
            },
        },
        "required": ["path"],
    }

    def __init__(self, runtime_client: RuntimeClient):
        self.runtime = runtime_client

    def execute(self, path: str, pattern: str = "*", show_hidden: bool = False) -> ToolResult:
        validation = self.runtime.validate_path(path, "read")
        if not validation.allowed:
            return ToolResult(
                success=False, output="", error=f"Access denied: {validation.denial_reason}"
            )

        try:
            dir_path = Path(validation.resolved_path)

            if not dir_path.exists():
                return ToolResult(success=False, output="", error=f"Directory not found: {path}")

            if not dir_path.is_dir():
                return ToolResult(success=False, output="", error=f"Not a directory: {path}")

            files = list(dir_path.glob(pattern))

            if not show_hidden:
                files = [f for f in files if not f.name.startswith(".")]

            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            files = files[:100]

            lines = []
            for f in files:
                try:
                    stat = f.stat()
                    size = stat.st_size
                    is_dir = f.is_dir()
                    type_str = "d" if is_dir else "f"
                    lines.append(f"{type_str} {size:>10} {f.name}")
                except OSError:
                    lines.append(f"?          ? {f.name}")

            output = "\n".join(lines) if lines else "(empty directory)"

            return ToolResult(
                success=True,
                output=output,
                data={
                    "count": len(files),
                    "path": str(dir_path),
                    "pattern": pattern,
                },
            )
        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error listing directory: {str(e)}")


class FileDeleteTool(BaseTool):
    """Delete a file from an allowed directory."""

    name = "file_delete"
    description = "Delete a file. Use with caution - this cannot be undone."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to delete."},
        },
        "required": ["path"],
    }

    def __init__(self, runtime_client: RuntimeClient):
        self.runtime = runtime_client

    def execute(self, path: str) -> ToolResult:
        validation = self.runtime.validate_path(path, "write")
        if not validation.allowed:
            return ToolResult(
                success=False, output="", error=f"Access denied: {validation.denial_reason}"
            )

        try:
            file_path = Path(validation.resolved_path)

            if not file_path.exists():
                return ToolResult(success=False, output="", error=f"File not found: {path}")

            if file_path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Cannot delete directory: {path}. Use for files only.",
                )

            file_path.unlink()

            return ToolResult(
                success=True, output=f"Deleted: {path}", data={"deleted_path": str(file_path)}
            )
        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error deleting file: {str(e)}")
