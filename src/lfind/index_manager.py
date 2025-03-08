"""
index_manager.py

This module provides functionality to update the file index stored in the SQLite database,
build a hierarchical tree representation from the indexed file metadata, and generate a
compact output for display.
"""

import os
import fnmatch

from .db_manager import DatabaseManager


def should_ignore(name, ignore_patterns):
    """
    Check if a file or directory name should be ignored based on the provided patterns.

    Parameters:
        name (str): The file or directory name.
        ignore_patterns (list of str): Patterns to match against.

    Returns:
        bool: True if the name matches any pattern; otherwise, False.
    """
    return any(fnmatch.fnmatch(name, pattern) for pattern in ignore_patterns)


def update_index(start_path, ignore_patterns, db_path=None):
    """
    Update the file index in the SQLite database by scanning the file system starting at start_path.

    This function performs the following steps:
      1. Resets the 'seen' flags for all records in the database.
      2. Walks the file system (using os.walk) and for each directory and file that is not ignored:
         - Inserts or updates the record (which automatically marks it as seen).
      3. After scanning, removes records that were not touched during the scan.

    Parameters:
        start_path (str): The root directory from which to start indexing.
        ignore_patterns (list of str): Patterns for file/directory names to ignore.
        db_path (str, optional): Path to the database file. If None, use default.
    """
    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = lambda x, **kwargs: x  # Simple passthrough if tqdm is not available
    
    db = DatabaseManager(db_path) if db_path else DatabaseManager()
    try:
        db.reset_seen_flags()
        
        # Count total files first for progress bar
        total_files = 0
        for _, _, files in os.walk(start_path):
            total_files += len(files)
        
        # Process with progress bar
        with tqdm(total=total_files, desc="Indexing files") as pbar:
            for root, dirs, files in os.walk(start_path):
                # Filter out directories to skip based on ignore patterns
                dirs[:] = [d for d in dirs if not should_ignore(d, ignore_patterns)]
                
                # Process each file in the current directory
                for file in files:
                    if not should_ignore(file, ignore_patterns):
                        file_path = os.path.join(root, file)
                        
                        # Get file stats
                        try:
                            stats = os.stat(file_path)
                            
                            # Create file metadata
                            file_data = {
                                "name": file,
                                "absolute_path": file_path,
                                "type": "file",
                                "size": stats.st_size,
                                "modified_at": stats.st_mtime
                            }
                            
                            # Update the database (this also marks the file as "seen")
                            db.touch_file(file_data)
                        except Exception as e:
                            print(f"Error processing file {file_path}: {e}")
                        
                        pbar.update(1)
        
        # Delete missing files
        deleted_count = db.delete_missing_files()
        print(f"Deleted {deleted_count} missing records from the index.")
        
        return True
    finally:
        # Make sure to close the database connection even if an exception occurs
        db.close()


def build_index_tree(directory, extensions=None):
    """
    Build a hierarchical tree representation of the indexed files starting from the given directory.

    This function queries the SQLite database for records whose absolute paths fall under the specified
    directory (optionally filtered by file extensions) and then builds a nested dictionary representing
    the directory structure.

    Parameters:
        directory (str): The root directory to build the tree from.
        extensions (list of str, optional): List of file extensions to filter (e.g., [".pdf", ".docx"]).
        
    Returns:
        dict: A nested dictionary representing the file tree.
    """
    db = DatabaseManager()
    records = db.get_files_by_criteria(directory=directory, extensions=extensions)
    db.close()

    root_abs = os.path.abspath(directory)
    tree = {
        "name": os.path.basename(root_abs) if os.path.basename(root_abs) else root_abs,
        "absolute_path": root_abs,
        "type": "directory",
        "children": []
    }

    for record in records:
        try:
            rel_path = os.path.relpath(record["absolute_path"], root_abs)
        except ValueError:
            # Skip records that are not under the given directory.
            continue
        parts = rel_path.split(os.sep)
        insert_into_tree(tree, parts, record)

    return tree


def insert_into_tree(tree, parts, record):
    """
    Recursively insert a record into the hierarchical tree based on the provided relative path parts.

    Parameters:
        tree (dict): The current tree node.
        parts (list of str): The remaining parts of the file path relative to the tree root.
        record (dict): The file metadata record to insert.
    """
    if not parts:
        return

    if len(parts) == 1:
        # Base case: add the file/directory as a child if not already present.
        for child in tree.get("children", []):
            if child["name"] == record["name"]:
                return
        tree.setdefault("children", []).append(record)
    else:
        # Recursive case: process the subdirectory.
        subdir = parts[0]
        sub_node = None
        for child in tree.get("children", []):
            if child["name"] == subdir and child["type"] == "directory":
                sub_node = child
                break
        if sub_node is None:
            sub_node = {
                "name": subdir,
                "absolute_path": os.path.join(tree["absolute_path"], subdir),
                "type": "directory",
                "children": []
            }
            tree.setdefault("children", []).append(sub_node)
        insert_into_tree(sub_node, parts[1:], record)


def build_index_output(tree, settings):
    """
    Generate a compact, human-friendly output from the hierarchical index tree.

    The settings dictionary may include:
      - max_entries: Maximum number of entries to display per directory (default: 100)
      - include_empty_dirs: Boolean flag indicating whether to display directories even if empty
      - ext_filters: (Optional) List of allowed file extensions (e.g., [".pdf", ".docx"])

    Returns:
        tuple: (output_lines, abs_paths)
            - output_lines (list of str): The compact text representation of the tree.
            - abs_paths (list of str): List of absolute file paths corresponding to the displayed files.
    """
    abs_paths = []

    def traverse(node):
        if not node:
            return []

        if node["type"] == "directory":
            children = node.get("children", [])
            collected = []
            count = 0
            for child in children:
                child_output = traverse(child)
                if child_output:
                    collected.extend(child_output)
                    count += 1
                    if count >= settings.get("max_entries", 100):
                        break
            output = []
            if collected or settings.get("include_empty_dirs", False):
                output.append(f"<Dir: {node['name']}>")
                output.extend(collected)
                output.append("</Dir>")
            return output

        elif node["type"] == "file":
            ext_filters = settings.get("ext_filters")
            if ext_filters:
                _, ext = os.path.splitext(node["name"])
                if ext.lower() not in ext_filters:
                    return []
            abs_paths.append(node["absolute_path"])
            return [node["name"]]

        return []
    
    output_lines = traverse(tree)
    return output_lines, abs_paths
