"""Configuration management for claudezh."""
import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "language": "auto",  # auto, zh-CN, zh-TW, en
    "theme": "dark",
    "model": "claude-sonnet-4-6",
    "mode": "auto",  # auto, sdk, api
    "auto_approve": False,
    "max_turns": 50,
    "show_token_usage": True,
    "history_size": 100,
    "thinking_mode": "auto",  # auto, deep, off
    "effort_level": "medium",  # low, medium, high, max
}


def get_config_dir() -> Path:
    """Get config directory (~/.claudezh/).

    Creates the directory if it does not exist.
    """
    config_dir = Path.home() / ".claudezh"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def load_config() -> dict:
    """Load config from file, merge with defaults.

    Missing keys are filled from DEFAULT_CONFIG so that new options
    are always available even with an older config file.
    """
    config_path = get_config_dir() / "config.json"
    config = dict(DEFAULT_CONFIG)

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
        except (json.JSONDecodeError, OSError):
            # Corrupted or unreadable file -- fall back to defaults
            pass

    return config


def save_config(config: dict):
    """Save config to file.

    Only keys that differ from DEFAULT_CONFIG are persisted so the
    file stays small and forward-compatible.
    """
    config_path = get_config_dir() / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_api_key() -> str:
    """Get Claude API key from env or config.

    Resolution order:
      1. ANTHROPIC_API_KEY environment variable
      2. ``api_key`` field in the config file
      3. Interactive prompt (the value is saved for next time)

    Returns the API key string.

    Raises:
        SystemExit: If running non-interactively and no key is found.
    """
    # 1. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # 2. Config file
    config = load_config()
    key = config.get("api_key", "").strip()
    if key:
        return key

    # 3. Prompt user
    if not os.isatty(0):
        raise SystemExit(
            "Error: ANTHROPIC_API_KEY not set and no api_key in config. "
            "Please set the environment variable or run interactively."
        )

    print("未找到 API Key。请输入你的 Anthropic API Key：")
    key = input("> ").strip()
    if not key:
        raise SystemExit("Error: API key cannot be empty.")

    config["api_key"] = key
    save_config(config)
    print("API Key 已保存到 ~/.claudezh/config.json")
    return key
