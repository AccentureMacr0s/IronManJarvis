"""Central configuration loader for the platform.

Loads config from config.yaml with environment variable overrides.
"""

import os
import yaml
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class Config:
    """Platform configuration manager."""

    def __init__(self, config_path: str | None = None):
        self._path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self.reload()

    def reload(self):
        """Load or reload configuration from file."""
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}
        self._apply_env_overrides()

    def _apply_env_overrides(self):
        """Override config values with PLATFORM_* environment variables.

        Example: PLATFORM_WEB__PORT=9000 sets config["web"]["port"] = 9000
        """
        prefix = "PLATFORM_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split("__")
                target = self._data
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = self._auto_cast(value)

    @staticmethod
    def _auto_cast(value: str) -> Any:
        """Attempt to cast string values to appropriate types."""
        if value.lower() in ("true", "yes"):
            return True
        if value.lower() in ("false", "no"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested config value using dot-path keys.

        Usage: config.get("web", "port", default=8000)
        """
        target = self._data
        for key in keys:
            if isinstance(target, dict):
                target = target.get(key)
            else:
                return default
            if target is None:
                return default
        return target

    @property
    def data(self) -> dict[str, Any]:
        """Return the full config dictionary."""
        return self._data


# Global config singleton
_config: Config | None = None


def get_config(config_path: str | None = None) -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
