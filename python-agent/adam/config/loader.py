"""
Configuration loading and saving utilities.
"""

import json
from pathlib import Path
from typing import Optional
from .schema import AdamConfig


DEFAULT_CONFIG_PATH = Path.home() / ".adam" / "config.json"


def load_config(path: Optional[Path] = None) -> AdamConfig:
    """
    Load configuration from file.

    Args:
        path: Path to config file. Defaults to ~/.adam/config.json

    Returns:
        AdamConfig instance
    """
    path = path or DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        return AdamConfig(**data)
    return AdamConfig()


def save_config(config: AdamConfig, path: Optional[Path] = None) -> None:
    """
    Save configuration to file.

    Args:
        config: AdamConfig instance to save
        path: Path to config file. Defaults to ~/.adam/config.json
    """
    path = path or DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2)


def get_default_config() -> dict:
    """Get default configuration as dictionary."""
    return AdamConfig().model_dump(mode="json")
