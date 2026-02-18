"""
Agent loop for Adam.

The core execution loop that connects:
- LLM providers (via ModelRouter)
- Tools (via ToolRegistry)
- Memory (via AdamMemory/SessionMemory)
- Runtime (via RuntimeClient)
"""

import asyncio
import uuid
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass, field

from ..providers import BaseProvider, Message, CompletionResponse, ToolCall, get_provider
from ..tools import ToolRegistry, ToolResult
from ..orchestration import ModelRouter, ExecutionMode
from ..orchestration.estimator import ComplexityTier
from ..memory import AdamMemory, SessionMemory
from ..runtime import RuntimeClient
from ..config import AdamConfig


class AgentError(Exception):
    """Custom exception for agent errors."""
    def __init__(self, message: str, original_error: str = None):
        self.message = message
        self.original_error = original_error or message
        super().__init__(message)


@dataclass
class LoopConfig:
    """Configuration for agent loop behavior."""

    model: str = "auto"
    mode: ExecutionMode = ExecutionMode.AUTO_PILOT
    max_turns: int = 50
    timeout_per_turn: int = 120
    provider: str = "anthropic"
    system_prompt: str = ""


@dataclass
class AgentState:
    """Mutable state during agent execution."""

    turns: int = 0
    tool_calls_made: int = 0
    last_model: str = ""
    errors: List[str] = field(default_factory=list)


class AgentLoop:
    """
    Main agent loop implementing the LLM ↔ Tool execution cycle.

    Flow:
    1. Receive user message
    2. Route to appropriate model
    3. Call LLM with tools available
    4. Execute any tool calls
    5. Loop until no more tool calls
    6. Return response
    """

    DEFAULT_SYSTEM_PROMPT = """You are Adam, a personal AI assistant with secure access to the user's local files and the ability to execute commands.

You have access to the following capabilities:
- File operations: Read, write, list, and delete files in allowed directories
- Shell execution: Run commands in a sandboxed environment
- Memory: Store and retrieve information for future reference
- Web access: Fetch content from URLs

Always be helpful, concise, and security-conscious. Never attempt to access files outside allowed directories. When in doubt, ask for clarification."""

    def __init__(
        self,
        config: LoopConfig,
        runtime_client: RuntimeClient,
        memory: AdamMemory = None,
        tool_registry: ToolRegistry = None,
        model_router: ModelRouter = None,
    ):
        """
        Initialize agent loop.

        Args:
            config: Agent loop configuration
            runtime_client: Client for runtime services
            memory: Long-term memory system
            tool_registry: Registry of available tools
            model_router: Model selection router
        """
        self.config = config
        self.runtime = runtime_client
        self.memory = memory
        self.session = SessionMemory()

        self.tools = tool_registry or ToolRegistry()
        self.router = model_router or ModelRouter()

        self._register_default_tools()

        self.state = AgentState()

        self._provider: Optional[BaseProvider] = None

    def _register_default_tools(self):
        """Register default tools."""
        from ..tools.filesystem import FileReadTool, FileWriteTool, FileListTool
        from ..tools.shell import ShellTool, PythonTool, WebFetchTool
        from ..tools.memory import MemoryStoreTool, MemorySearchTool

        self.tools.register(FileReadTool(self.runtime))
        self.tools.register(FileListTool(self.runtime))

        self.tools.register(ShellTool(self.runtime))
        self.tools.register(PythonTool(self.runtime))
        self.tools.register(WebFetchTool(self.runtime))

        if self.memory:
            self.tools.register(MemoryStoreTool(self.memory))
            self.tools.register(MemorySearchTool(self.memory))

    def _get_provider(self) -> BaseProvider:
        """Get or create LLM provider."""
        if self._provider is None:
            self._provider = get_provider(self.config.provider)
            if not self._provider:
                raise AgentError(f"Provider not available: {self.config.provider}")
        return self._provider

    def _get_system_prompt(self) -> str:
        """Get system prompt."""
        return self.config.system_prompt or self.DEFAULT_SYSTEM_PROMPT

    async def run(
        self,
        user_message: str,
        on_response: Callable[[str], None] = None,
        on_tool_call: Callable[[str, dict], None] = None,
    ) -> str:
        """
        Run the agent loop with a user message.

        Args:
            user_message: User's input message
            on_response: Callback for response chunks (for streaming)
            on_tool_call: Callback when tools are called

        Returns:
            Final response string

        Raises:
            AgentError: When an API or execution error occurs
        """
        self.session.add("user", user_message)

        self.state = AgentState()

        while self.state.turns < self.config.max_turns:
            self.state.turns += 1

            model, routing = self._select_model(user_message)
            self.state.last_model = model

            messages = self._build_messages()

            try:
                provider = self._get_provider()
                response = await provider.complete(
                    messages=messages,
                    model=model,
                    tools=self.tools.get_anthropic_tools(),
                )
            except AgentError:
                raise  # Re-raise our custom errors
            except Exception as e:
                error_msg = str(e)
                self.state.errors.append(error_msg)
                raise AgentError(f"API Error: {error_msg}", error_msg)

            if response.content:
                self.session.add("assistant", response.content)
                if on_response:
                    on_response(response.content)

            if response.tool_calls:
                for tool_call in response.tool_calls:
                    self.state.tool_calls_made += 1

                    if on_tool_call:
                        on_tool_call(tool_call.name, tool_call.arguments)

                    result = self.tools.execute(tool_call.name, tool_call.arguments)

                    if result.success:
                        tool_message = f"Tool '{tool_call.name}' result:\n{result.output}"
                    else:
                        tool_message = f"Tool '{tool_call.name}' error:\n{result.error}"

                    self.session.add("user", tool_message)

                continue

            return response.content

        return "I reached the maximum number of turns. Please try a simpler request."

    def _select_model(self, task: str) -> tuple:
        """Select model based on configuration."""
        if self.config.model != "auto":
            return self.config.model, None

        from ..orchestration.router import RoutingDecision

        decision = self.router.select_model(
            task=task,
            mode=self.config.mode,
        )
        return decision.model, decision

    def _build_messages(self) -> List[Message]:
        """Build message list for LLM."""
        messages = []

        messages.append(Message(role="system", content=self._get_system_prompt()))

        for msg in self.session.format_for_llm():
            messages.append(Message(role=msg["role"], content=msg["content"]))

        return messages

    def clear_session(self):
        """Clear session memory."""
        self.session.clear()
        self.state = AgentState()

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "turns": self.state.turns,
            "tool_calls": self.state.tool_calls_made,
            "last_model": self.state.last_model,
            "session_messages": len(self.session),
            "errors": self.state.errors,
        }


async def run_agent(
    message: str, config: AdamConfig = None, runtime_client: RuntimeClient = None, **kwargs
) -> str:
    """
    Convenience function to run agent once.

    Args:
        message: User message
        config: Adam configuration
        runtime_client: Runtime client
        **kwargs: Additional agent config options

    Returns:
        Agent response
    """
    if runtime_client is None:
        runtime_client = RuntimeClient()

    loop_config = LoopConfig(
        model=kwargs.get("model", "auto"),
        mode=kwargs.get("mode", ExecutionMode.AUTO_PILOT),
        provider=kwargs.get("provider", "anthropic"),
    )

    agent = AgentLoop(
        config=loop_config,
        runtime_client=runtime_client,
    )

    return await agent.run(message)
