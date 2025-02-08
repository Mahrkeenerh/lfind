import os
from typing import List, Optional, Dict

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMClient:
    """Represents a single LLM client configuration"""
    def __init__(self, provider: str, model: str, api_base: Optional[str]):
        self.provider = provider
        self.model = model
        self.api_base = api_base
        self.client = OpenAI(
            base_url=api_base,
            api_key='ollama' if provider == "ollama" else os.getenv("OPENAI_API_KEY")
        )

    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Send completion request to the LLM."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error during {self.provider} API call: {e}")
            return ""


class LLMService:
    def __init__(self, config: Dict):
        """Initialize LLM service with configuration."""
        self.config = config

        # Initialize default and hard clients
        default_config = config.get("llm_default", {})
        hard_config = config.get("llm_hard", {})

        self.default_client = LLMClient(
            provider=default_config.get("provider", "ollama"),
            model=default_config.get("model", "qwen2.5:14b-instruct-q6_K"),
            api_base=default_config.get("api_base", "http://localhost:11434/v1")
        )

        self.hard_client = LLMClient(
            provider=hard_config.get("provider", "openai"),
            model=hard_config.get("model", "gpt-4o"),
            api_base=hard_config.get("api_base")
        )

    def create_search_prompt(self, query: str, file_list: List[str]) -> str:
        """Create a prompt for file search."""
        return f"""Given the following list of files:

{'\n'.join(file_list)}

Find files that best match this search query: "{query}"

Instructions:
- Return ONLY the matching filenames, one per line
- Do not include any explanations or additional text
- Do not include directory structures or absolute paths
- If no files match, return an empty response"""

    def search_files(self, query: str, file_list: List[str], use_hard_model: bool = False) -> List[str]:
        """Search for files using LLM."""
        client = self.hard_client if use_hard_model else self.default_client

        messages = [
            {
                "role": "system",
                "content": "You are a file search assistant that helps find relevant files based on natural language queries."
            },
            {
                "role": "user",
                "content": self.create_search_prompt(query, file_list)
            }
        ]

        print(f"Using {client.provider} model '{client.model}' for search")

        response = client.complete(messages)

        # Split response into lines and filter out empty lines
        results = [line.strip() for line in response.split('\n') if line.strip()]
        return results

    def get_absolute_paths(self, filenames: List[str], abs_paths: List[str]) -> List[str]:
        """Match filenames to their absolute paths."""
        results = []
        for filename in filenames:
            for abs_path in abs_paths:
                if os.path.basename(abs_path) == filename:
                    results.append(abs_path)
                    break
        return results
