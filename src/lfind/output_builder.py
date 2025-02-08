import os

def build_compact_output(tree, settings):
    """Build compact output with filtering."""
    abs_paths = []

    def traverse(node):
        """
        Traverse the tree and return the compact output lines.
        compact_lines: List of compact output lines
        """
        if not node:
            return False

        if node["type"] == "directory":
            children = node.get("children", [])
            filtered_outputs = []
            children_count = 0

            # Determine if this directory should be output
            should_output = settings["include_empty_dirs"]

            # Process all children first
            for child in children:
                child_output = traverse(child)
                should_output = should_output or child_output
                if child_output:
                    children_count += 1
                    filtered_outputs.extend(child_output)
                    if children_count >= settings["max_entries"]:
                        break

            output = []

            if should_output:
                output = [
                    f"<Dir: {node['name']}>",
                    *[out for out in filtered_outputs],
                    "</Dir>"
                ]
            return output

        elif node["type"] == "file":
            if settings["ext_filters"]:
                _, ext = os.path.splitext(node["name"])
                if ext.lower() not in settings["ext_filters"]:
                    return []

            abs_paths.append(node["absolute_path"])
            return [node["name"]]

        return []

    output = traverse(tree)
    return output, abs_paths
