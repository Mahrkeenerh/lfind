import json
import os
from pathlib import Path
import shutil
import sys


def get_default_config_path():
    """Get the default config file path from the package."""
    import lfind
    package_dir = os.path.dirname(lfind.__file__)
    return os.path.join(package_dir, "config.json")


def get_user_config_path():
    """Get the user's config file path."""
    if sys.platform == "win32":
        config_dir = os.path.join(os.environ["APPDATA"], "lfind")
    else:
        config_dir = os.path.join(str(Path.home()), ".config", "lfind")

    return os.path.join(config_dir, "config.json")


def ensure_user_config():
    """Ensure user config exists, create if it doesn't."""
    user_config_path = get_user_config_path()
    if not os.path.exists(user_config_path):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(user_config_path), exist_ok=True)

        # Copy default config to user config location
        default_config_path = get_default_config_path()
        shutil.copy2(default_config_path, user_config_path)

    return user_config_path


def load_config(config_path=None):
    """
    Load configuration from a JSON file; return a dictionary of settings.
    If no config_path is provided, use the user config or create it from default.
    """
    defaults = {
        "max_entries": 100,
        "ignore_patterns": [".*"],  # Default pattern to ignore all dot files/folders
        "include_empty_dirs": False,
        "cache_dir": ".lfind_cache",  # Directory to store all caches
        "meta_cache": "meta_cache.json",
        "cache_validity_days": 7
    }

    # If no specific path provided, use user config
    if config_path is None:
        config_path = ensure_user_config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        defaults.update(user_config)
    except Exception as e:
        print(f"Warning: Could not load config file '{config_path}': {e}\nUsing default settings.", 
              file=sys.stderr)

    return defaults


def get_config_location():
    """Get the location of the currently used config file."""
    return get_user_config_path()
