"""
Memory system for Adam using Mem0 with Chroma backend.

Provides both short-term (session) and long-term (persistent) memory.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

try:
    from mem0 import Memory

    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False


@dataclass
class MemoryItem:
    """A single memory item."""

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    score: float = 0.0


class AdamMemory:
    """
    Adam's memory system using Mem0 with Chroma.

    Provides:
    - Long-term semantic memory via Mem0/Chroma
    - Session-scoped working memory
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize memory system.

        Args:
            config: Configuration dict with keys:
                - chroma_path: Path to Chroma database
                - user_id: User identifier for memory scoping
                - llm_provider: LLM provider ("openai", "ollama")
                - llm_model: Model name for the LLM
                - openai_api_key: OpenAI API key (or use OPENAI_API_KEY env)
                - ollama_base_url: Ollama base URL (default: http://localhost:11434)
        """
        self.config = config or {}
        self.chroma_path = Path(
            self.config.get("chroma_path", "~/.adam/memory/chroma")
        ).expanduser()
        self.user_id = self.config.get("user_id", "default")

        self._mem0 = None
        self._initialized = False

    def _get_llm_config(self) -> Optional[Dict[str, Any]]:
        """Build LLM configuration based on settings."""
        llm_provider = self.config.get("llm_provider", "openai")

        if llm_provider == "ollama":
            return {
                "provider": "ollama",
                "config": {
                    "model": self.config.get("llm_model", "llama3.2:latest"),
                    "ollama_base_url": self.config.get("ollama_base_url", "http://localhost:11434"),
                },
            }
        else:
            api_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            return {
                "provider": "openai",
                "config": {
                    "model": self.config.get("llm_model", "gpt-4o-mini"),
                    "api_key": api_key,
                },
            }

    def _init_mem0(self):
        """Initialize Mem0 client lazily."""
        if self._initialized:
            return

        if not MEM0_AVAILABLE:
            print("Warning: mem0ai not installed. Memory features limited.")
            self._initialized = True
            return

        try:
            self.chroma_path.parent.mkdir(parents=True, exist_ok=True)

            llm_config = self._get_llm_config()
            if not llm_config:
                print(
                    "Warning: No LLM configured for Mem0. Set OPENAI_API_KEY or configure ollama."
                )
                self._initialized = True
                return

            config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "adam_memory",
                        "path": str(self.chroma_path),
                    },
                },
                "embedder": {
                    "provider": "huggingface",
                    "config": {
                        "model": "sentence-transformers/all-MiniLM-L6-v2",
                    },
                },
                "llm": llm_config,
            }

            self._mem0 = Memory.from_config(config)
            self._initialized = True

        except Exception as e:
            print(f"Warning: Failed to initialize Mem0: {e}")
            self._initialized = True

    def store(self, content: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Store a memory.

        Args:
            content: Content to remember
            metadata: Optional metadata

        Returns:
            Memory ID if successful
        """
        self._init_mem0()

        if not self._mem0:
            return None

        try:
            result = self._mem0.add(content, user_id=self.user_id, metadata=metadata or {})

            if result and isinstance(result, list) and len(result) > 0:
                return result[0].get("id")
            return None

        except Exception as e:
            print(f"Error storing memory: {e}")
            return None

    def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """
        Search memories semantically.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memories
        """
        self._init_mem0()

        if not self._mem0:
            return []

        try:
            results = self._mem0.search(query, user_id=self.user_id, limit=limit)

            items = []
            for r in results:
                items.append(
                    MemoryItem(
                        id=r.get("id", ""),
                        content=r.get("memory", ""),
                        metadata=r.get("metadata", {}),
                        score=r.get("score", 0.0),
                    )
                )

            return items

        except Exception as e:
            print(f"Error searching memory: {e}")
            return []

    def get_all(self) -> List[MemoryItem]:
        """Get all memories."""
        self._init_mem0()

        if not self._mem0:
            return []

        try:
            results = self._mem0.get_all(user_id=self.user_id)

            items = []
            for r in results:
                items.append(
                    MemoryItem(
                        id=r.get("id", ""),
                        content=r.get("memory", ""),
                        metadata=r.get("metadata", {}),
                    )
                )

            return items

        except Exception as e:
            print(f"Error getting memories: {e}")
            return []

    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        self._init_mem0()

        if not self._mem0:
            return False

        try:
            self._mem0.delete(memory_id)
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False

    def clear(self) -> bool:
        """Clear all memories for this user."""
        self._init_mem0()

        if not self._mem0:
            return False

        try:
            self._mem0.delete_all(user_id=self.user_id)
            return True
        except Exception as e:
            print(f"Error clearing memories: {e}")
            return False


class SessionMemory:
    """
    Short-term session memory.

    Maintains conversation history and working context.
    """

    def __init__(self, max_messages: int = 50):
        """
        Initialize session memory.

        Args:
            max_messages: Maximum messages to keep
        """
        self.max_messages = max_messages
        self._messages: List[Dict[str, Any]] = []

    def add(self, role: str, content: str, metadata: Dict = None):
        """Add a message to session memory."""
        self._messages.append(
            {
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }
        )

        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages."""
        return self._messages[-n:]

    def format_for_llm(self, n: int = None) -> List[Dict[str, str]]:
        """Format messages for LLM input."""
        messages = self._messages if n is None else self._messages[-n:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def clear(self):
        """Clear session memory."""
        self._messages = []

    def __len__(self) -> int:
        return len(self._messages)
