"""
Configuration schemas for Adam.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from pathlib import Path


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    api_key: Optional[str] = None
    api_base: Optional[str] = None
    enabled: bool = True

    class Config:
        extra = "allow"


class ProvidersConfig(BaseModel):
    """Configuration for all LLM providers."""

    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    ollama: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(api_base="http://localhost:11434")
    )
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)

    class Config:
        extra = "allow"


class TierModelsConfig(BaseModel):
    """Model selection for each complexity tier."""

    quick: str = "anthropic/claude-3-haiku"
    standard: str = "anthropic/claude-3.5-sonnet"
    deep: str = "anthropic/claude-opus-4"


class AgentConfig(BaseModel):
    """Agent behavior configuration."""

    default_mode: str = "auto_pilot"
    tier_models: TierModelsConfig = Field(default_factory=TierModelsConfig)
    workspace: Path = Field(default=Path("~/.adam/workspace"))
    max_turns: int = 50
    timeout_per_turn: int = 120

    @field_validator("workspace", mode="before")
    @classmethod
    def expand_workspace(cls, v):
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


class ProfileConfig(BaseModel):
    """Security profile configuration."""

    name: str = "balanced"


class AdamConfig(BaseModel):
    """Root configuration for Adam."""

    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)

    class Config:
        extra = "allow"
