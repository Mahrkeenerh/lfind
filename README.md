# lfind

A natural language file finder using LLMs. This tool allows you to search for files using natural language queries, powered by large language models. Simply describe what you're looking for, and lfind will help you locate the relevant files.

## Installation

```bash
pip install lfind
```

## Configuration

lfind uses a configuration file to manage its settings. The default configuration is installed with the package, and a user-specific configuration is automatically created on first run at:

- Windows: `%APPDATA%\lfind\config.json`
- Unix/Linux: `~/.config/lfind/config.json`

### Default Configuration

```json
{
    "max_entries": 100,
    "ignore_patterns": [
        ".*"
    ],
    "include_empty_dirs": false,
    "cache_dir": ".lfind_cache",
    "meta_cache": "meta_cache.json",
    "cache_validity_days": 7,
    "llm_default": {
        "provider": "ollama",
        "model": "qwen2.5:14b-instruct-q6_K",
        "api_base": "http://localhost:11434/v1"
    },
    "llm_hard": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_base": null
    }
}
```

### Environment Variables

If you're using OpenAI models (default for the "hard" mode), you need to set your OpenAI API key:

```bash
export OPENAI_API_KEY=your_api_key_here  # Unix/Linux
setx OPENAI_API_KEY your_api_key_here     # Windows
```

## Usage

```bash
# Basic search in current directory
lfind "First invoice of 2025"

# Search with specific file extensions
lfind -e pdf docx "presentation on attention mechanisms"

# Search in specific directory
lfind -d /path/to/dir "log files from last week"

# Use more powerful LLM model (e.g., GPT-4o)
lfind -H "files related to database migrations"

# Ignore default ignore patterns (ommiting . (dot) files)
lfind --ignore-defaults "configuration files"

# Add custom ignore patterns
lfind -i "*.tmp" "*.bak" "important documents"
```

### Additional Options

- `--empty keep/ignore`: Override empty directories behavior
- `--max N`: Set maximum entries per directory
- `-r, --refresh-cache`: Force rebuild the cache
- `--config`: Set custom configuration file
- `-v, --version`: Show version information

## Caching

lfind maintains a cache of the directory structure to improve performance. The cache is automatically created and updated as needed, with a default validity period of 7 days. You can force a cache refresh using the `-r` flag.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Requirements

- Python ≥ 3.8
- openai ≥ 1.61.1
- python-dotenv ≥ 1.0.1

## Note

When using OpenAI models (default for hard mode), ensure you have set your OPENAI_API_KEY environment variable. For local models like Ollama, ensure the service is running and accessible at the configured API base URL.
