import os
from typing import Dict, List, Type, Set, Optional
from .base import FileEmbedder

class EmbedderRegistry:
    """Registry for file embedders."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure we only have one registry."""
        if cls._instance is None:
            cls._instance = super(EmbedderRegistry, cls).__new__(cls)
            cls._instance._embedders = {}
            cls._instance._extension_map = {}
        return cls._instance
    
    def register(self, embedder: FileEmbedder, name: str = None) -> None:
        """Register a new embedder.
        
        Args:
            embedder: The embedder instance
            name: Optional name for the embedder. If None, class name will be used.
        """
        if name is None:
            name = embedder.__class__.__name__
        
        self._embedders[name] = embedder
        
        # Update extension mappings
        for ext in embedder.supported_extensions:
            if ext in self._extension_map:
                print(f"Warning: Extension {ext} already handled by "
                      f"{self._extension_map[ext]}, overriding with {name}")
            self._extension_map[ext] = name
    
    def get_for_file(self, file_path: str) -> Optional[FileEmbedder]:
        """Get the appropriate embedder for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileEmbedder: The embedder that can handle this file,
            or None if no suitable embedder is found
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self._extension_map:
            return self._embedders[self._extension_map[ext]]
        
        # Try to find an embedder that can handle this file
        for name, embedder in self._embedders.items():
            if embedder.can_embed(file_path):
                return embedder
        
        return None
    
    def get_all_supported_extensions(self) -> Set[str]:
        """Get all extensions supported by registered embedders."""
        return set(self._extension_map.keys())
    
    def list_embedders(self) -> List[str]:
        """List all registered embedders."""
        return list(self._embedders.keys())
    
    def has_embedder_for(self, file_path: str) -> bool:
        """Check if there's an embedder available for the given file."""
        return self.get_for_file(file_path) is not None

# Global registry instance
registry = EmbedderRegistry()
