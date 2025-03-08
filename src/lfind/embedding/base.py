from abc import ABC, abstractmethod
import os
from typing import Dict, List, Any, Set, Optional
import numpy as np

class FileEmbedder(ABC):
    """Base class for all file embedders."""
    
    @property
    @abstractmethod
    def supported_extensions(self) -> Set[str]:
        """Return a set of file extensions this embedder can handle."""
        pass
    
    def can_embed(self, file_path: str) -> bool:
        """Check if this embedder can handle the given file."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Extract text content from the file for embedding.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
        """
        pass
    
    @abstractmethod
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from the file that might be useful for search.
        
        This could include things like:
        - Title
        - Description/Summary
        - Keywords
        - Author
        - Created/Modified dates
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict[str, Any]: Metadata extracted from the file
        """
        pass
