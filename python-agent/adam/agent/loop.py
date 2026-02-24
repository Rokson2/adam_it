"""
Agent loop for Adam - simplified.

Uses providers that handle their own model selection.
"""

import asyncio
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass, field

from ..providers import BaseProvider, Message, CompletionResponse, ToolCall, get_provider
from ..tools import ToolRegistry
from ..runtime import RuntimeClient
from ..orchestration import ExecutionMode
from ..memory import SessionMemory


class AgentError(Exception):
    """Agent error."""
    pass


@dataclass
class LoopConfig:
    """Agent configuration."""
    model: str = "auto"  # Let provider decide
    mode: ExecutionMode = ExecutionMode.AUTO_PILOT
    max_turns: int = 50
    timeout: int = 120
    provider: str = "anthropic"
    system_prompt: str = ""


@dataclass 
class AgentState:
    """Agent state."""
    turns: int = 0
    tool_calls: int = 0
    last_model: str = ""
    errors: List[str] = field(default_factory=list)


class AgentLoop:
    """
    Main agent loop.
    
    Simplified: providers handle model selection.
    """
    
    DEFAULT_SYSTEM = """You are Adam, a helpful AI assistant.

You can help with questions, coding, file operations, and running commands.
Be helpful, concise, and accurate."""
    
    def __init__(
        self,
        config: LoopConfig,
        runtime_client: RuntimeClient = None,
        tool_registry: ToolRegistry = None,
    ):
        self.config = config
        self.runtime = runtime_client
        self.tools = tool_registry or ToolRegistry()
        self.session = SessionMemory()
        self.state = AgentState()
        self._provider: Optional[BaseProvider] = None
        
        # Register default tools if runtime available
        if runtime_client:
            self._register_tools()
    
    def _register_tools(self):
        """Register available tools."""
        from ..tools.filesystem import FileReadTool, FileListTool
        from ..tools.shell import ShellTool
        
        self.tools.register(FileReadTool(self.runtime))
        self.tools.register(FileListTool(self.runtime))
        self.tools.register(ShellTool(self.runtime))
    
    def _get_provider(self) -> BaseProvider:
        """Get or create provider."""
        if self._provider is None:
            from adam.security import keystore
            
            api_key = keystore.get(self.config.provider)
            self._provider = get_provider(self.config.provider, api_key=api_key)
            
            if not self._provider:
                raise AgentError(f"Unknown provider: {self.config.provider}")
        
        return self._provider
    
    async def run(
        self,
        user_message: str,
        on_response: Callable[[str], None] = None,
    ) -> str:
        """
        Run agent with user message.
        
        Returns final response.
        """
        self.session.add("user", user_message)
        self.state = AgentState()
        
        while self.state.turns < self.config.max_turns:
            self.state.turns += 1
            
            provider = self._get_provider()
            messages = self._build_messages()
            tools = self.tools.get_openai_tools()  # OpenAI format works for most
            
            try:
                response = await provider.complete(
                    messages=messages,
                    model=self.config.model,
                    tools=tools,
                )
                self.state.last_model = response.model
            except Exception as e:
                self.state.errors.append(str(e))
                raise AgentError(str(e))
            
            # Handle response
            if response.content:
                self.session.add("assistant", response.content)
                if on_response:
                    on_response(response.content)
            
            # Handle tool calls
            if response.tool_calls:
                for tc in response.tool_calls:
                    self.state.tool_calls += 1
                    result = self.tools.execute(tc.name, tc.arguments)
                    
                    tool_msg = f"Tool {tc.name}: {result.output if result.success else result.error}"
                    self.session.add("user", tool_msg)
                
                continue  # Loop for next turn
            
            return response.content
        
        return "Maximum turns reached."
    
    def _build_messages(self) -> List[Message]:
        """Build message list for LLM."""
        messages = []
        
        # System prompt
        messages.append(Message(
            role="system",
            content=self.config.system_prompt or self.DEFAULT_SYSTEM
        ))
        
        # Conversation history
        for msg in self.session.format_for_llm():
            messages.append(Message(
                role=msg["role"],
                content=msg["content"]
            ))
        
        return messages
    
    def clear_session(self):
        """Clear session."""
        self.session.clear()
        self.state = AgentState()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stats."""
        return {
            "turns": self.state.turns,
            "tool_calls": self.state.tool_calls,
            "last_model": self.state.last_model,
            "errors": self.state.errors,
        }


async def run_agent(
    message: str,
    provider: str = "anthropic",
    model: str = "auto",
    **kwargs
) -> str:
    """Quick agent run."""
    config = LoopConfig(provider=provider, model=model)
    agent = AgentLoop(config=config)
    return await agent.run(message)
