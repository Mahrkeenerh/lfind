import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any

from . import config
from .db_manager import DatabaseManager
from .embedding.service import EmbeddingService
from .llm_service import LLMService
from .search_pipeline import SearchPipeline
from . import index_manager

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Version information
__version__ = "0.2.0"
__author__ = "Mahrkeenerh"
__description__ = "Natural language file search tool with LLM support"


def print_version():
    """Print version information and exit."""
    print(f"{__description__} v{__version__}")
    print(f"Author: {__author__}")

    config_path = config.get_config_location()
    print(f"Config file location: {config_path}")


def parse_date(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")


def parse_size(size_str: str) -> int:
    """Parse a size string like '5MB' into bytes."""
    if not size_str:
        return 0
        
    size_str = size_str.upper()
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024
    }
    
    # Handle different formats: 5MB, 5 MB
    size_str = size_str.replace(" ", "")
    
    # Find the unit
    unit = 'B'
    for u in units:
        if size_str.endswith(u):
            unit = u
            size_str = size_str[:-len(u)]
            break
    
    try:
        size_value = float(size_str)
        return int(size_value * units[unit])
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid size format: {size_str}{unit}")


def setup_common_arguments(parser):
    """Add common arguments to a parser or subparser."""
    parser.add_argument("-d", "--directory", default=".", help="Search directory path")
    parser.add_argument("-i", "--ignore", nargs="+", help="Additional ignore patterns")
    parser.add_argument("--ignore-defaults", action="store_true", help="Ignore default patterns")
    parser.add_argument("--config", type=str, help="Path to configuration file")


def setup_search_parser(subparsers):
    """Set up the search subparser with all relevant arguments."""
    search_parser = subparsers.add_parser("search", help="Search for files")
    search_parser.add_argument("query", help="Natural language query to search for files")
    setup_common_arguments(search_parser)
    
    # File filtering options
    search_parser.add_argument("-e", "--extensions", nargs="+", help="Only include files with specified extensions")
    
    # Date filtering options
    search_parser.add_argument("--created-after", type=parse_date, help="Filter files created after date (YYYY-MM-DD)")
    search_parser.add_argument("--created-before", type=parse_date, help="Filter files created before date (YYYY-MM-DD)")
    search_parser.add_argument("--modified-after", type=parse_date, help="Filter files modified after date (YYYY-MM-DD)")
    search_parser.add_argument("--modified-before", type=parse_date, help="Filter files modified before date (YYYY-MM-DD)")
    
    # Size filtering options
    search_parser.add_argument("--min-size", type=parse_size, help="Minimum file size (e.g., '5MB', '1KB')")
    search_parser.add_argument("--max-size", type=parse_size, help="Maximum file size (e.g., '100MB', '2GB')")
    
    # Search options
    search_parser.add_argument("-r", "--refresh-cache", action="store_true", help="Force rebuild the cache")
    search_parser.add_argument("-H", "--hard", action="store_true", help="Use the more powerful LLM model")
    search_parser.add_argument("--semantic", action="store_true", help="Use semantic search")
    search_parser.add_argument("--no-llm", action="store_true", help="Disable LLM search")
    search_parser.add_argument("--top", type=int, default=10, help="Number of top results to show")
    
    return search_parser


def setup_embed_parser(subparsers):
    """Set up the embed subparser for embedding management."""
    embed_parser = subparsers.add_parser("embed", help="Manage file embeddings")
    setup_common_arguments(embed_parser)
    embed_parser.add_argument("-r", "--rebuild", action="store_true", help="Rebuild all embeddings")
    embed_parser.add_argument("-u", "--update", action="store_true", help="Update only changed files")
    embed_parser.add_argument("-t", "--types", nargs="+", default=["text", "pdf"], 
                            help="File types to embed (e.g., text, pdf, docx)")
    embed_parser.add_argument("--batch-size", type=int, default=100, 
                            help="Number of files to process in one batch")
    return embed_parser


def setup_index_parser(subparsers):
    """Set up the index subparser for database management."""
    index_parser = subparsers.add_parser("index", help="Manage the file index")
    setup_common_arguments(index_parser)
    index_parser.add_argument("--rebuild", action="store_true", 
                             help="Force rebuild the entire index")
    index_parser.add_argument("--status", action="store_true",
                             help="Show index statistics and status")
    index_parser.add_argument("--cleanup", action="store_true",
                             help="Clean up missing files from the index")
    return index_parser


def setup_setup_parser(subparsers):
    """Set up the setup subparser for initial configuration."""
    setup_parser = subparsers.add_parser("setup", help="Initial setup and configuration")
    setup_common_arguments(setup_parser)
    setup_parser.add_argument("--model", choices=["openai", "sentence-transformers"], 
                             default="sentence-transformers", help="Embedding model to use")
    setup_parser.add_argument("--llm-provider", choices=["openai", "ollama"], 
                             default="ollama", help="LLM provider for search")
    return setup_parser


def handle_search_command(args, cfg):
    """Handle the search command."""
    # Set up paths
    cache_dir = cfg["cache_dir"]
    os.makedirs(cache_dir, exist_ok=True)
    db_path = os.path.join(cache_dir, "metadata.db")

    # Process arguments and config
    ignore_patterns = list(cfg["ignore_patterns"])
    if args.ignore_defaults:
        ignore_patterns = []
    if args.ignore:
        ignore_patterns.extend(args.ignore)

    ext_filters = None
    if args.extensions:
        ext_filters = [
            f".{ext.lower()}" if not ext.startswith('.') else ext.lower() 
            for ext in args.extensions
        ]

    # Process directory
    start_path = os.path.abspath(args.directory)
    if not os.path.exists(start_path):
        print(f"Error: Path '{start_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Initialize database manager
    db = DatabaseManager(db_path)
    
    # Update the index if needed or requested
    if args.refresh_cache:
        print("Rebuilding file index...")
        index_manager.update_index(start_path, ignore_patterns)
    
    # Initialize the embedding service
    try:
        embedding_service = EmbeddingService()
        print("Initialized embedding service")
    except Exception as e:
        if args.semantic:
            print(f"Error initializing embedding service: {e}", file=sys.stderr)
            print("Semantic search will be disabled.", file=sys.stderr)
            args.semantic = False
        embedding_service = None

    # Initialize LLM service
    llm = LLMService(cfg)

    if args.hard and not cfg.get("llm_hard"):
        print("Warning: Hard model not specified in config, using default model", file=sys.stderr)

    # Create search pipeline
    search_pipeline = SearchPipeline(db, embedding_service, llm, cfg)
    
    # Build filter criteria
    filter_criteria = {}
    
    # Add date filters
    if args.created_after:
        filter_criteria["created_after"] = args.created_after
    if args.created_before:
        filter_criteria["created_before"] = args.created_before
    if args.modified_after:
        filter_criteria["modified_after"] = args.modified_after
    if args.modified_before:
        filter_criteria["modified_before"] = args.modified_before
        
    # Add size filters
    if args.min_size is not None:
        filter_criteria["min_size"] = args.min_size
    if args.max_size is not None:
        filter_criteria["max_size"] = args.max_size
    
    # Perform search
    results = search_pipeline.multi_search(
        query=args.query,
        directory=start_path,
        extensions=ext_filters,
        use_semantic=args.semantic,
        use_llm=not args.no_llm,
        use_hard_llm=args.hard,
        top_k=args.top,
        filter_criteria=filter_criteria
    )
    
    # Display results
    if results:
        print(f"\nFound {len(results)} matching files:")
        for result in results:
            path = result.get('absolute_path', '')
            if path:
                print(path)
    else:
        print("\nNo matching files found.")

    # Close database connection
    db.close()


def handle_embed_command(args, cfg):
    """Handle the embed command."""
    print("Managing embeddings...")
    
    # Set up paths
    cache_dir = cfg["cache_dir"]
    os.makedirs(cache_dir, exist_ok=True)
    db_path = os.path.join(cache_dir, "metadata.db")
    
    # Process directory
    start_path = os.path.abspath(args.directory)
    if not os.path.exists(start_path):
        print(f"Error: Path '{start_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize database and embedding service
    db = DatabaseManager(db_path)
    
    try:
        embedding_service = EmbeddingService()
        print("Initialized embedding service")
    except Exception as e:
        print(f"Error initializing embedding service: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get files to process
    if args.rebuild:
        print("Rebuilding all embeddings...")
        files_to_process = db.get_files_by_criteria(start_path, type="file")
    else:
        # Get only files that have changed since last embedding
        print("Updating embeddings for changed files...")
        files_to_process = db.get_files_by_criteria(
            start_path, 
            type="file",
            needs_embedding_update=True
        )
    
    if not files_to_process:
        print("No files need embedding updates.")
        db.close()
        return
    
    print(f"Found {len(files_to_process)} files to process")
    
    # Process files in batches with progress display
    batch_size = args.batch_size
    total_batches = (len(files_to_process) + batch_size - 1) // batch_size
    
    successful = 0
    failed = 0
    
    for i in range(0, len(files_to_process), batch_size):
        batch = files_to_process[i:i+batch_size]
        print(f"Processing batch {(i // batch_size) + 1}/{total_batches} ({len(batch)} files)")
        
        for file in tqdm(batch) if HAS_TQDM else batch:
            file_path = file.get("absolute_path")
            if not file_path or not os.path.exists(file_path):
                failed += 1
                continue
                
            try:
                embedding, metadata = embedding_service.embed_file(file_path)
                if embedding is not None:
                    # Save embedding to database
                    db.update_embedding(file["id"], embedding)
                    successful += 1
                else:
                    print(f"Failed to generate embedding for {file_path}: {metadata.get('error', 'Unknown error')}")
                    failed += 1
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
                failed += 1
    
    print(f"Embedding processing complete: {successful} successful, {failed} failed")
    db.close()


def handle_index_command(args, cfg):
    """Handle the index command."""
    # Set up paths
    cache_dir = cfg["cache_dir"]
    os.makedirs(cache_dir, exist_ok=True)
    db_path = os.path.join(cache_dir, "metadata.db")
    
    # Process arguments and config
    ignore_patterns = list(cfg["ignore_patterns"])
    if args.ignore_defaults:
        ignore_patterns = []
    if args.ignore:
        ignore_patterns.extend(args.ignore)
    
    # Process directory
    start_path = os.path.abspath(args.directory)
    if not os.path.exists(start_path):
        print(f"Error: Path '{start_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize database manager
    db = DatabaseManager(db_path)
    
    if args.rebuild:
        print("Rebuilding file index...")
        index_manager.update_index(start_path, ignore_patterns)
    elif args.cleanup:
        print("Cleaning up missing files from index...")
        db.reset_seen_flags()
        deleted_count = db.delete_missing_files()
        print(f"Deleted {deleted_count} missing records from the index.")
    elif args.status:
        # Show index statistics
        file_count = db.get_file_count()
        dir_count = db.get_directory_count()
        last_update = db.get_last_update_time()
        
        print("Index status:")
        print(f"  Total files indexed: {file_count}")
        print(f"  Total directories indexed: {dir_count}")
        if last_update:
            print(f"  Last index update: {last_update}")
        else:
            print("  Last index update: Never")
    else:
        print("No index operation specified. Use --rebuild, --cleanup, or --status.")
    
    db.close()


def handle_setup_command(args, cfg):
    """Handle the setup command."""
    print("Running initial setup...")
    
    # Update configuration
    updated_cfg = dict(cfg)
    if args.model:
        updated_cfg["embedding_model"] = args.model
    if args.llm_provider:
        updated_cfg["llm_provider"] = args.llm_provider
    
    # Save updated config
    config_path = config.get_user_config_path()
    with open(config_path, 'w') as f:
        import json
        json.dump(updated_cfg, f, indent=2)
    
    print(f"Configuration saved to {config_path}")
    
    # Set up paths
    cache_dir = updated_cfg["cache_dir"]
    os.makedirs(cache_dir, exist_ok=True)
    db_path = os.path.join(cache_dir, "metadata.db")
    
    # Process directory
    start_path = os.path.abspath(args.directory)
    if not os.path.exists(start_path):
        print(f"Error: Path '{start_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize database
    print("Initializing database...")
    db = DatabaseManager(db_path)
    
    # Build initial index
    print("Building initial file index...")
    ignore_patterns = updated_cfg["ignore_patterns"]
    if args.ignore:
        ignore_patterns.extend(args.ignore)
    if args.ignore_defaults:
        ignore_patterns = []
        
    index_manager.update_index(start_path, ignore_patterns)
    
    print("Setup complete! You can now use lfind to search for files.")
    db.close()


def main():
    """Main entry point for the lfind command."""
    config.ensure_user_config()

    # Create main parser
    parser = argparse.ArgumentParser(
        description="Search for files using natural language queries with LLM support."
    )
    parser.add_argument("-v", "--version", action="store_true", help="Show version information and exit")
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Set up command parsers
    search_parser = setup_search_parser(subparsers)
    embed_parser = setup_embed_parser(subparsers)
    index_parser = setup_index_parser(subparsers)
    setup_parser = setup_setup_parser(subparsers)
    
    # Backwards compatibility: Allow search as default command
    parser.add_argument("query", nargs="?", help="Natural language query to search for files (shorthand for search command)")
    parser.add_argument("-d", "--directory", default=".", help="Search directory path")
    parser.add_argument("-e", "--extensions", nargs="+", help="Only include files with specified extensions")
    parser.add_argument("-i", "--ignore", nargs="+", help="Additional ignore patterns")
    parser.add_argument("--ignore-defaults", action="store_true", help="Ignore default patterns")
    parser.add_argument("-r", "--refresh-cache", action="store_true", help="Force rebuild the cache")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("-H", "--hard", action="store_true", help="Use the more powerful LLM model")
    parser.add_argument("--semantic", action="store_true", help="Use semantic search")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM search")
    parser.add_argument("--top", type=int, default=10, help="Number of top results to show")
    
    # Parse arguments
    args = parser.parse_args()

    # Handle version flag
    if args.version:
        print_version()
        sys.exit(0)
    
    # Load configuration
    cfg = config.load_config(args.config)
    
    # Handle commands
    if args.command == "search":
        handle_search_command(args, cfg)
    elif args.command == "embed":
        handle_embed_command(args, cfg)
    elif args.command == "index":
        handle_index_command(args, cfg)
    elif args.command == "setup":
        handle_setup_command(args, cfg)
    elif args.query:  # Default to search if a query is provided
        # For compatibility with old CLI, execute search
        handle_search_command(args, cfg)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
