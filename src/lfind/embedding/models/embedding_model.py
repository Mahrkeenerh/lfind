from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np

class EmbeddingModel(ABC):
    """Base class for embedding models."""
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embeddings produced by this model."""
        pass
    
    @abstractmethod
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            numpy array containing the embedding
        """
        pass
    
    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            2D numpy array with embeddings
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this embedding model."""
        pass
    
    @abstractmethod
    def get_provider(self) -> str:
        """Return the provider of this embedding model."""
        pass
