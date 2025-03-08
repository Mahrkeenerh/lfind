from typing import List, Optional
import numpy as np
import os

from .embedding_model import EmbeddingModel

class SentenceTransformerModel(EmbeddingModel):
    """Embedding model using SentenceTransformers library."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the model.
        
        Args:
            model_name: Name of the SentenceTransformers model to use
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            self._dimension = self.model.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError(
                "SentenceTransformers is not installed. "
                "Install it with 'pip install sentence-transformers'."
            )
    
    def get_embedding_dimension(self) -> int:
        return self._dimension
    
    def get_embedding(self, text: str) -> np.ndarray:
        return self.model.encode(text, show_progress_bar=False)
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, show_progress_bar=True)
    
    def get_name(self) -> str:
        return self.model_name
    
    def get_provider(self) -> str:
        return "SentenceTransformers"
