"""
Task complexity estimation for model routing.

Analyzes user requests to determine appropriate model tier:
- Quick (Tier 1): Simple lookups, formatting
- Standard (Tier 2): Analysis, implementation
- Deep (Tier 3): Architecture, debugging, security
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Dict, List, Any, Optional


class ComplexityTier(Enum):
    """Model complexity tiers."""

    QUICK = 1
    STANDARD = 2
    DEEP = 3


@dataclass
class TaskAnalysis:
    """Result of complexity analysis."""

    tier: ComplexityTier
    score: int
    signals: Dict[str, List[str]]
    confidence: float
    reasoning: str


COMPLEXITY_SIGNALS = {
    "quick": {
        "patterns": [
            r"\b(what|show|list|read|display|get|find)\b",
            r"\b(simple|quick|just|only|basic)\b",
            r"\b(format|convert|parse)\b",
            r"\b(copy|move|rename)\b",
            r"\b(hello|hi|hey|thanks)\b",
        ],
        "weight": -2,
    },
    "standard": {
        "patterns": [
            r"\b(add|create|modify|update|edit|change)\b",
            r"\b(analyze|summarize|explain|describe)\b",
            r"\b(implement|build|write|develop)\b",
            r"\b(test|validate|verify)\b",
            r"\b(review|check|inspect)\b",
            r"\b(file|files|directory|folder)\b",
            r"\b(function|method|class|module)\b",
        ],
        "weight": 0,
    },
    "deep": {
        "patterns": [
            r"\b(debug|fix|troubleshoot|solve)\b",
            r"\b(refactor|restructure|redesign|reorganize)\b",
            r"\b(architecture|design|system|framework)\b",
            r"\b(security|vulnerability|exploit|attack)\b",
            r"\b(performance|optimize|improve|scale)\b",
            r"\b(race condition|deadlock|memory leak|concurrency)\b",
            r"\b(integrate|integration|api|service)\b",
            r"\b(complex|complicated|advanced|sophisticated)\b",
        ],
        "weight": 3,
    },
}

CONTEXT_WEIGHTS = {
    "file_count": {
        1: 0,
        3: 1,
        10: 2,
    },
    "total_lines": {
        100: 0,
        500: 1,
        2000: 2,
    },
    "has_tests": -1,
    "is_new_feature": 1,
    "is_bug_fix": 2,
}


def estimate_complexity(task: str, context: Dict[str, Any] = None) -> TaskAnalysis:
    """
    Estimate task complexity based on linguistic signals and context.

    Args:
        task: User's task/request description
        context: Optional context (files, lines, etc.)

    Returns:
        TaskAnalysis with tier, score, signals, and reasoning
    """
    task_lower = task.lower()
    score = 0
    matched_signals: Dict[str, List[str]] = {
        "quick": [],
        "standard": [],
        "deep": [],
    }

    for category, config in COMPLEXITY_SIGNALS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, task_lower):
                matched_signals[category].append(pattern)
                score += config["weight"]

    reasoning_parts = []
    if context:
        file_count = len(context.get("files", []))
        for threshold, adjustment in sorted(CONTEXT_WEIGHTS["file_count"].items()):
            if file_count >= threshold:
                score += adjustment
        if file_count > 1:
            reasoning_parts.append(f"{file_count} files involved")

        total_lines = context.get("total_lines", 0)
        for threshold, adjustment in sorted(CONTEXT_WEIGHTS["total_lines"].items()):
            if total_lines >= threshold:
                score += adjustment
        if total_lines > 500:
            reasoning_parts.append(f"{total_lines} lines of code")

        if context.get("has_tests"):
            score += CONTEXT_WEIGHTS["has_tests"]
        if context.get("is_new_feature"):
            score += CONTEXT_WEIGHTS["is_new_feature"]
        if context.get("is_bug_fix"):
            score += CONTEXT_WEIGHTS["is_bug_fix"]

    if score < 0:
        tier = ComplexityTier.QUICK
        reasoning = "Simple task with straightforward patterns"
    elif score < 3:
        tier = ComplexityTier.STANDARD
        reasoning = "Standard implementation or analysis task"
    else:
        tier = ComplexityTier.DEEP
        reasoning = "Complex task requiring deep reasoning"

    if matched_signals["quick"]:
        reasoning_parts.append(f"quick signals: {len(matched_signals['quick'])}")
    if matched_signals["standard"]:
        reasoning_parts.append(f"standard signals: {len(matched_signals['standard'])}")
    if matched_signals["deep"]:
        reasoning_parts.append(f"deep signals: {len(matched_signals['deep'])}")

    reasoning = f"{reasoning} (score: {score})"
    if reasoning_parts:
        reasoning += f" - {', '.join(reasoning_parts)}"

    total_signals = sum(len(s) for s in matched_signals.values())
    confidence = min(1.0, 0.5 + (total_signals * 0.1))

    return TaskAnalysis(
        tier=tier,
        score=score,
        signals=matched_signals,
        confidence=confidence,
        reasoning=reasoning,
    )


def get_tier_description(tier: ComplexityTier) -> str:
    """Get human-readable description of a tier."""
    descriptions = {
        ComplexityTier.QUICK: "Quick tasks: simple lookups, formatting, basic operations",
        ComplexityTier.STANDARD: "Standard tasks: implementation, analysis, multi-step operations",
        ComplexityTier.DEEP: "Deep tasks: architecture, debugging, security, complex reasoning",
    }
    return descriptions[tier]


def suggest_model(tier: ComplexityTier, config: Dict[str, str] = None) -> str:
    """
    Suggest a model for the given tier.

    Args:
        tier: Complexity tier
        config: Optional config with tier_models mapping

    Returns:
        Model identifier
    """
    if config:
        tier_models = config.get("tier_models", {})
        tier_name = tier.name.lower()
        if tier_name in tier_models:
            return tier_models[tier_name]

    defaults = {
        ComplexityTier.QUICK: "anthropic/claude-3-haiku",
        ComplexityTier.STANDARD: "anthropic/claude-3.5-sonnet",
        ComplexityTier.DEEP: "anthropic/claude-opus-4",
    }
    return defaults[tier]
