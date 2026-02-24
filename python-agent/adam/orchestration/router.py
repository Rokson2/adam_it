"""
Model router for Adam.
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .estimator import ComplexityTier, estimate_complexity


class ExecutionMode(Enum):
    """How to choose models."""
    USER_PICKED = "user_picked"
    WORKFLOW = "workflow"
    AUTO_PILOT = "auto_pilot"


@dataclass
class RoutingDecision:
    """Result of model routing."""
    model: str
    provider: str
    tier: ComplexityTier
    mode: ExecutionMode
    reasoning: str


# Default tier models - provider agnostic
# Provider will map these to actual model names
DEFAULT_TIER_MODELS = {
    ComplexityTier.QUICK: "auto",      # Fast model
    ComplexityTier.STANDARD: "auto",   # Standard model
    ComplexityTier.DEEP: "auto",       # Deep thinking model
}

# Map model prefixes to providers
MODEL_PROVIDERS = {
    "claude": "anthropic",
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "glm": "z-ai",
    "llama": "ollama",
    "mistral": "ollama",
    "qwen": "ollama",
}


class ModelRouter:
    """Routes tasks to appropriate models."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tier_models = self._load_tier_models()
        self.default_mode = ExecutionMode(self.config.get("default_mode", "auto_pilot"))
        self.default_model = self.config.get("default_model", "auto")

    def _load_tier_models(self) -> Dict[ComplexityTier, str]:
        """Load tier-to-model mappings."""
        tier_models = DEFAULT_TIER_MODELS.copy()

        if "tier_models" in self.config:
            for tier_name, model in self.config["tier_models"].items():
                tier = ComplexityTier[tier_name.upper()]
                tier_models[tier] = model

        return tier_models

    def select_model(
        self,
        task: str,
        mode: ExecutionMode = None,
        explicit_model: str = None,
        workflow_model: str = None,
        context: Dict[str, Any] = None,
    ) -> RoutingDecision:
        """Select appropriate model for a task."""
        mode = mode or self.default_mode

        if explicit_model:
            return RoutingDecision(
                model=explicit_model,
                provider=self._get_provider(explicit_model),
                tier=self._estimate_tier_from_model(explicit_model),
                mode=ExecutionMode.USER_PICKED,
                reasoning=f"User-specified model: {explicit_model}",
            )

        if mode == ExecutionMode.WORKFLOW and workflow_model:
            return RoutingDecision(
                model=workflow_model,
                provider=self._get_provider(workflow_model),
                tier=self._estimate_tier_from_model(workflow_model),
                mode=ExecutionMode.WORKFLOW,
                reasoning=f"Workflow-specified model: {workflow_model}",
            )

        analysis = estimate_complexity(task, context)
        model = self.tier_models.get(analysis.tier, self.default_model)

        return RoutingDecision(
            model=model,
            provider=self._get_provider(model),
            tier=analysis.tier,
            mode=ExecutionMode.AUTO_PILOT,
            reasoning=f"Auto-selected based on complexity: {analysis.reasoning}",
        )

    def _get_provider(self, model: str) -> str:
        """Determine provider from model name."""
        if model == "auto":
            return "auto"  # Will be resolved by agent
        
        model_lower = model.lower()

        for prefix, provider in MODEL_PROVIDERS.items():
            if model_lower.startswith(prefix):
                return provider

        if "/" in model:
            return model.split("/")[0]

        return "unknown"

    def _estimate_tier_from_model(self, model: str) -> ComplexityTier:
        """Estimate tier from model name."""
        model_lower = model.lower()

        if any(x in model_lower for x in ["haiku", "mini", "lite", "flash", "turbo"]):
            return ComplexityTier.QUICK
        elif any(x in model_lower for x in ["opus", "o1", "o3", "max", "plus"]):
            return ComplexityTier.DEEP
        else:
            return ComplexityTier.STANDARD

    def get_model_for_tier(self, tier: ComplexityTier) -> str:
        """Get the configured model for a tier."""
        return self.tier_models.get(tier, self.default_model)

    def set_tier_model(self, tier: ComplexityTier, model: str):
        """Update the model for a tier."""
        self.tier_models[tier] = model
