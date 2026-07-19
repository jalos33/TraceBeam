"""Configuration loader for NetPulse."""

from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir

_CONFIG_PATHS = [
    Path(user_config_dir("NetPulse", "NetPulse")) / "config.yaml",
    Path("config.yaml"),
    Path(__file__).parent.parent / "config.yaml",
]

_default_config = {
    "server": {
        "host": "127.0.0.1",   # local-only by default; single-user desktop app
        "port": 8742,
    },
    "lan": {
        "ping_targets": ["8.8.8.8", "1.1.1.1", "google.com"],
        "sample_interval_seconds": 2,
        "mtr_interval_seconds": 45,
        "mtr_cycles": 5,
        "raw_retention_hours": 48,
        "retention_days": 30,
    },
}


def get_config() -> dict[str, Any]:
    """Load config from YAML or return defaults."""
    config = _default_config.copy()

    for path in _CONFIG_PATHS:
        if path.exists():
            try:
                with open(path) as f:
                    loaded = yaml.safe_load(f) or {}
                # Deep merge
                for section, values in loaded.items():
                    if section in config and isinstance(config[section], dict):
                        config[section].update(values)
                    else:
                        config[section] = values
                break
            except Exception as e:
                print(f"Warning: Could not load {path}: {e}")

    return config


def get_nested(config_dict: dict, section: str, key: str, default: Any = None) -> Any:
    """Safe nested config access: get_nested(config, 'lan', 'sample_interval_seconds')"""
    section_dict = config_dict.get(section, {})
    return section_dict.get(key, default)
