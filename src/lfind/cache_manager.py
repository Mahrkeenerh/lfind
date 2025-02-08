from datetime import datetime, timedelta, UTC
import json
import os
import sys


def get_root_path(path):
    """Get the root (drive) path for a given path."""
    if sys.platform == "win32":
        return os.path.splitdrive(path)[0] + "\\"
    return "/"


def load_meta_cache(meta_cache_path):
    """Load or initialize the meta cache that tracks all cache files."""
    if os.path.exists(meta_cache_path):
        try:
            with open(meta_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load meta cache '{meta_cache_path}': {e}", file=sys.stderr)
    return {}


def save_meta_cache(meta_cache_path, meta_cache):
    """Save the meta cache to disk."""
    try:
        os.makedirs(os.path.dirname(meta_cache_path), exist_ok=True)
        with open(meta_cache_path, "w", encoding="utf-8") as f:
            json.dump(meta_cache, f, indent=2)
    except Exception as e:
        print(f"Error saving meta cache: {e}", file=sys.stderr)


def update_meta_cache(meta_cache, cache_name, root_path):
    """Update meta cache with information about a cache file."""
    meta_cache[cache_name] = {
        "root": os.path.abspath(root_path),
        "drive": get_drive_identifier(root_path),
        "last_updated": datetime.now(UTC).isoformat(),
    }


def is_cache_valid(meta_cache, cache_name, root_path, validity_days):
    """Check if a cache is valid using the meta cache."""
    cache_info = meta_cache.get(cache_name)
    if not cache_info:
        return False

    if os.path.abspath(root_path) != cache_info["root"]:
        return False

    try:
        cache_date = datetime.fromisoformat(cache_info["last_updated"])
        if datetime.now(UTC) - cache_date > timedelta(days=validity_days):
            return False
    except Exception:
        return False

    return True


def get_drive_identifier(path):
    """Get a unique identifier for the drive containing the path."""
    if sys.platform == "win32":
        return os.path.splitdrive(path)[0] or "C:"
    return "root"  # For Unix-like systems, use a single identifier


def generate_cache_name(root_path):
    """Generate a unique cache name based on the root path."""
    drive_id = get_drive_identifier(root_path)
    safe_drive_id = "".join(c if c.isalnum() else "" for c in drive_id)
    return f"cache_{safe_drive_id}.json"


def save_cache(cache_path, tree, root):
    """Save the full tree to a cache file."""
    cache_data = {
        "root": os.path.abspath(root),
        "tree": tree
    }
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}", file=sys.stderr)


def load_cache_file(cache_path):
    """Load cache data from cache file."""
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load cache file '{cache_path}': {e}", file=sys.stderr)
        return None


def find_subtree(tree, target_path):
    """Find a subtree in the cached tree structure based on the target path."""
    if not tree:
        return None

    target_path = os.path.abspath(target_path)
    current_path = tree["absolute_path"]

    if current_path == target_path:
        return tree

    if tree["type"] != "directory":
        return None

    if not target_path.startswith(current_path):
        return None

    for child in tree.get("children", []):
        result = find_subtree(child, target_path)
        if result:
            return result

    return None
