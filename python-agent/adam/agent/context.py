"""
Context building utilities for Adam agent.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path


class ContextBuilder:
    """Builds context for complexity estimation and agent execution."""

    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path.home() / ".adam" / "workspace"

    def build_context(
        self,
        user_message: str,
        files: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Build context dictionary for complexity estimation.

        Args:
            user_message: User's message
            files: List of file paths involved

        Returns:
            Context dictionary
        """
        context = {
            "workspace": str(self.workspace),
            "files": files or [],
            "total_lines": 0,
            "file_types": set(),
        }

        if files:
            for file_path in files:
                try:
                    path = Path(file_path).expanduser()
                    if path.exists() and path.is_file():
                        with open(path, "r") as f:
                            lines = len(f.readlines())
                        context["total_lines"] += lines

                        ext = path.suffix.lower()
                        context["file_types"].add(ext)
                except:
                    pass

        context["file_types"] = list(context["file_types"])

        return context
