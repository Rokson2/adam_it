"""
Shell execution tool for Adam.

Executes shell commands in a sandboxed container for security.
"""

import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, List
import subprocess
import uuid

from .base import BaseTool, ToolResult
from ..runtime import RuntimeClient


class ShellTool(BaseTool):
    """Execute shell commands in a sandboxed environment."""

    name = "shell"
    description = (
        "Execute a shell command in a sandboxed environment. "
        "Use for running scripts, system commands, or any shell operations. "
        "Commands run in isolation and cannot access files outside allowed directories."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute. Can be a single command or a script with multiple lines.",
            },
            "timeout": {
                "type": "integer",
                "default": 60,
                "description": "Timeout in seconds. Maximum execution time before the command is terminated.",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command. Must be an allowed path.",
            },
            "env": {
                "type": "object",
                "description": "Environment variables to set for the command.",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["command"],
    }

    def __init__(self, runtime_client: RuntimeClient):
        self.runtime = runtime_client

    def execute(
        self, command: str, timeout: int = 60, cwd: str = None, env: Dict[str, str] = None
    ) -> ToolResult:
        """
        Execute a shell command.

        Note: Currently uses direct subprocess execution.
        Container execution will be enabled when Docker is available.
        """
        if cwd:
            validation = self.runtime.validate_path(cwd, "read")
            if not validation.allowed:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Working directory access denied: {validation.denial_reason}",
                )
            cwd = validation.resolved_path

        script_id = str(uuid.uuid4())[:8]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=f".sh", prefix=f"adam-{script_id}-", delete=False
        ) as f:
            f.write("#!/bin/bash\n")
            f.write("set -e\n")
            f.write("\n")
            f.write(command)
            script_path = f.name

        try:
            os.chmod(script_path, 0o700)

            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            exec_env["DEBIAN_FRONTEND"] = "noninteractive"
            exec_env["TERM"] = "dumb"

            result = subprocess.run(
                ["bash", script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=exec_env,
            )

            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr

            output_parts = []
            if stdout.strip():
                output_parts.append(stdout.strip())
            if stderr.strip():
                output_parts.append(f"[stderr]\n{stderr.strip()}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            return ToolResult(
                success=(exit_code == 0),
                output=output,
                error=stderr.strip() if exit_code != 0 else None,
                data={
                    "exit_code": exit_code,
                    "timeout": timeout,
                    "cwd": cwd or os.getcwd(),
                },
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout} seconds",
                data={"exit_code": 124, "timeout": True},
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Execution error: {str(e)}")

        finally:
            try:
                os.unlink(script_path)
            except:
                pass


class PythonTool(BaseTool):
    """Execute Python code in a sandboxed environment."""

    name = "python"
    description = (
        "Execute Python code. Use for calculations, data processing, "
        "or any Python operations. Code runs in the current Python environment."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Can be multiple lines.",
            },
            "timeout": {"type": "integer", "default": 60, "description": "Timeout in seconds."},
        },
        "required": ["code"],
    }

    def __init__(self, runtime_client: RuntimeClient = None):
        self.runtime = runtime_client

    def execute(self, code: str, timeout: int = 60) -> ToolResult:
        """Execute Python code and capture output."""
        import sys
        from io import StringIO
        import traceback

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        stdout_capture = StringIO()
        stderr_capture = StringIO()

        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        namespace = {
            "__builtins__": __builtins__,
            "__name__": "__main__",
        }

        error = None

        try:
            exec(code, namespace)
        except SyntaxError as e:
            error = f"SyntaxError: {e}"
        except Exception as e:
            error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        stdout_text = stdout_capture.getvalue()
        stderr_text = stderr_capture.getvalue()

        output_parts = []
        if stdout_text.strip():
            output_parts.append(stdout_text.strip())
        if stderr_text.strip():
            output_parts.append(f"[stderr]\n{stderr_text.strip()}")

        output = "\n".join(output_parts) if output_parts else "(no output)"

        return ToolResult(
            success=(error is None), output=output, error=error, data={"timeout": timeout}
        )


class WebFetchTool(BaseTool):
    """Fetch content from a URL."""

    name = "web_fetch"
    description = (
        "Fetch content from a URL. Use to retrieve web pages, APIs, or any HTTP-accessible content."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch."},
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
                "default": "GET",
                "description": "HTTP method.",
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers.",
                "additionalProperties": {"type": "string"},
            },
            "body": {"type": "string", "description": "Request body for POST requests."},
            "timeout": {
                "type": "integer",
                "default": 30,
                "description": "Request timeout in seconds.",
            },
        },
        "required": ["url"],
    }

    def __init__(self, runtime_client: RuntimeClient = None):
        self.runtime = runtime_client

    def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        body: str = None,
        timeout: int = 30,
    ) -> ToolResult:
        """Fetch content from a URL."""
        try:
            import httpx

            with httpx.Client() as client:
                if method == "GET":
                    response = client.get(
                        url, headers=headers, timeout=timeout, follow_redirects=True
                    )
                else:
                    response = client.post(
                        url, headers=headers, content=body, timeout=timeout, follow_redirects=True
                    )

            content = response.text
            if len(content) > 50000:
                content = content[:50000] + "\n... (truncated)"

            return ToolResult(
                success=response.status_code < 400,
                output=content,
                error=None if response.status_code < 400 else f"HTTP {response.status_code}",
                data={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                },
            )

        except httpx.TimeoutException:
            return ToolResult(
                success=False, output="", error=f"Request timed out after {timeout} seconds"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Request failed: {str(e)}")
