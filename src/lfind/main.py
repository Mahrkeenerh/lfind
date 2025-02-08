import os
import sys
import argparse

from . import cache_manager
from . import config
from .llm_service import LLMService
from . import output_builder
from . import tree_builder


# Version information
__version__ = "0.1.0"
__author__ = "Mahrkeenerh"
__description__ = "Natural language file search tool with LLM support"


def print_version():
    """Print version information and exit."""
    print(f"{__description__} v{__version__}")
    print(f"Author: {__author__}")

    config_path = config.get_config_location()
    print(f"Config file location: {config_path}")


def process_directory(start_path, cfg, mc, args, ignore_patterns):
    """Process directory with root-based caching strategy."""
    root_path = cache_manager.get_root_path(start_path)
    cache_name = cache_manager.generate_cache_name(root_path)
    cache_path = os.path.join(cfg["cache_dir"], cache_name)

    # Check if we have a valid cache for the root
    full_tree = None
    if not args.refresh_cache:
        if cache_manager.is_cache_valid(mc, cache_name, root_path, cfg["cache_validity_days"]):
            cache_data = cache_manager.load_cache_file(cache_path)
            if cache_data:
                full_tree = cache_data.get("tree")
                print(f"Using cache: {cache_name}")

    # Build new tree for entire root if needed
    if full_tree is None:
        print(f"Building tree for {root_path}")
        full_tree = tree_builder.build_full_tree(root_path, ignore_patterns)
        if full_tree:
            cache_manager.save_cache(cache_path, full_tree, root_path)
            cache_manager.update_meta_cache(mc, cache_name, root_path)
            cache_manager.save_meta_cache(
                os.path.join(cfg["cache_dir"], cfg["meta_cache"]), 
                mc
            )
            print("Cache saved.")

    # Find subtree for requested path if it's not the root
    if start_path != root_path:
        subtree = cache_manager.find_subtree(full_tree, start_path)
        if subtree:
            return subtree
        print(f"Warning: Could not find path {start_path} in cache", file=sys.stderr)
        return None

    return full_tree


def main():
    config.ensure_user_config()

    parser = argparse.ArgumentParser(
        description="Search for files using natural language queries with LLM support."
    )
    parser.add_argument("query", nargs="?", help="Natural language query to search for files")
    parser.add_argument("-d", "--directory", default=".", help="Search directory path")
    parser.add_argument("-e", "--extensions", nargs="+", help="Only include files with specified extensions")
    parser.add_argument("-i", "--ignore", nargs="+", help="Additional ignore patterns")
    parser.add_argument("--ignore-defaults", action="store_true", help="Ignore default patterns")
    parser.add_argument("--empty", choices=["keep", "ignore"], help="Override empty directories behavior")
    parser.add_argument("--max", type=int, help="Maximum entries per directory")
    parser.add_argument("-r", "--refresh-cache", action="store_true", help="Force rebuild the cache")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("-H", "--hard", action="store_true", help="Use the more powerful LLM model")
    parser.add_argument("-v", "--version", action="store_true", help="Show version information and exit")
    args = parser.parse_args()

    # Handle version flag
    if args.version:
        print_version()
        sys.exit(0)

    # Check if there's a query to process
    if not args.query:
        parser.print_help()
        sys.exit(1)

    # Load configuration
    cfg = config.load_config(args.config)

    # Set up paths
    cache_dir = cfg["cache_dir"]
    meta_cache_path = os.path.join(cache_dir, cfg["meta_cache"])

    # Load meta cache
    mc = cache_manager.load_meta_cache(meta_cache_path)

    # Process arguments and config
    ignore_patterns = list(cfg["ignore_patterns"])
    if args.ignore_defaults:
        ignore_patterns = []
    if args.ignore:
        ignore_patterns.extend(args.ignore)

    max_entries = args.max if args.max is not None else cfg["max_entries"]
    include_empty_dirs = (args.empty == "keep") if args.empty else cfg["include_empty_dirs"]

    ext_filters = None
    if args.extensions:
        ext_filters = [
            f".{ext.lower()}" if not ext.startswith('.') else ext.lower() 
            for ext in args.extensions
        ]

    # Initialize LLM service
    llm = LLMService(cfg)

    if args.hard and not cfg.get("llm_hard"):
        print("Warning: Hard model not specified in config, using default model", file=sys.stderr)

    # Process directory
    start_path = os.path.abspath(args.directory)
    if not os.path.exists(start_path):
        print(f"Error: Path '{start_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Process directory with root-based caching
    tree = process_directory(start_path, cfg, mc, args, ignore_patterns)
    if not tree:
        print("Error: Could not process directory tree.", file=sys.stderr)
        sys.exit(1)

    # Build output with settings
    settings = {
        "max_entries": max_entries,
        "include_empty_dirs": include_empty_dirs,
        "ext_filters": ext_filters
    }

    file_list, abs_paths = output_builder.build_compact_output(tree, settings)

    if not abs_paths:
        print("\nNo files found matching the criteria.")
        sys.exit(0)

    # Search using LLM
    matches = llm.search_files(args.query, file_list, args.hard)

    # Get and print absolute paths for matches
    results = llm.get_absolute_paths(matches, abs_paths)

    if results:
        print("\nFound matches:")
        for path in results:
            print(path)
    else:
        print("\nNo matching files found.")


if __name__ == "__main__":
    main()
