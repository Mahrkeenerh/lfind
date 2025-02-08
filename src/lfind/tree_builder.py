import fnmatch
import os


def should_ignore(name, ignore_patterns):
    """Check if a file or directory should be ignored based on patterns."""
    return any(fnmatch.fnmatch(name, pattern) for pattern in ignore_patterns)


def build_full_tree(root, ignore_patterns):
    """
    Recursively build a complete tree structure starting from root.
    Uses absolute paths throughout the tree structure.
    """
    if os.path.isdir(root):
        name = os.path.basename(root) if os.path.basename(root) else root
        if should_ignore(name, ignore_patterns):
            return None

        node = {
            "name": name,
            "absolute_path": os.path.abspath(root),
            "type": "directory",
            "children": []
        }

        try:
            entries = os.listdir(root)
            entries.sort()
        except Exception as e:
            node["error"] = str(e)
            return node

        for entry in entries:
            entry_path = os.path.join(root, entry)
            child_tree = build_full_tree(entry_path, ignore_patterns)
            if child_tree:  # Only add non-ignored entries
                node["children"].append(child_tree)
        return node

    elif os.path.isfile(root):
        name = os.path.basename(root)
        if should_ignore(name, ignore_patterns):
            return None
        return {
            "name": name,
            "absolute_path": os.path.abspath(root),
            "type": "file"
        }
    return None
