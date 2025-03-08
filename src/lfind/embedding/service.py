import os
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple

from .registry import registry
from .models import get_model, EmbeddingModel
from ..embed_manager import EmbedManager

class EmbeddingService:
    """Service for embedding files and managing embeddings."""
    
    def __init__(
        self, 
        model_provider: str = "sentence-transformers",
        model_name: str = "all-MiniLM-L6-v2",
        embed_manager: Optional[EmbedManager] = None,
        metric: str = "cosine"
    ):
        """Initialize the embedding service.
        
        Args:
            model_provider: Provider of the embedding model
            model_name: Name of the specific model to use
            embed_manager: Optional EmbedManager instance
            metric: Distance metric for embedding comparisons
        """
        # Initialize the embedding model
        self.model = get_model(model_provider, model_name)
        
        # Create or use the provided EmbedManager
        if embed_manager:
            self.embed_manager = embed_manager
        else:
            dim = self.model.get_embedding_dimension()
            self.embed_manager = EmbedManager(dim=dim, metric=metric)
    
    def embed_file(self, file_path: str, embedding_type: str = 'content', max_length: int = 10000) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        """Embed a file with better error handling"""
        try:
            # Get the appropriate embedder
            embedder = registry.get_for_file(file_path)
            if not embedder:
                return None, {"error": f"No suitable embedder found for file: {file_path}"}
            
            # Extract text
            try:
                text = embedder.extract_text(file_path, max_length)
            except Exception as e:
                return None, {"error": f"Failed to extract text from {file_path}: {str(e)}"}
                
            # Get embedding
            try:
                embedding = self.embed_model.get_embedding(text)
                return embedding, {"success": True, "file_path": file_path}
            except Exception as e:
                return None, {"error": f"Failed to generate embedding for {file_path}: {str(e)}"}
                
        except Exception as e:
            return None, {"error": f"Unexpected error embedding {file_path}: {str(e)}"}
    
    def batch_embed_files(
        self, 
        file_paths: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Create embeddings for multiple files.
        
        Args:
            file_paths: List of file paths to embed
            
        Returns:
            Dict mapping file paths to dicts with 'embedding' and 'metadata' keys
        """
        results = {}
        for file_path in file_paths:
            embedding, metadata = self.embed_file(file_path)
            if embedding is not None:
                results[file_path] = {
                    'embedding': embedding,
                    'metadata': metadata
                }
        return results
    
    def embed_query(self, query: str) -> np.ndarray:
        """Create an embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector
        """
        return self.model.get_embedding(query)
    
    def search_similar(
        self, 
        query: str, 
        k: int = 10
    ) -> List[Tuple[int, float]]:
        """Search for embeddings similar to the query.
        
        Args:
            query: Text query
            k: Number of results to return
            
        Returns:
            List of (id, similarity_score) tuples
        """
        # Create query embedding
        query_embedding = self.embed_query(query)
        
        # Search in FAISS index
        distances, indices = self.embed_manager.search(query_embedding, k)
        
        # Convert to list of (id, distance) pairs
        results = [
            (int(idx), float(dist)) 
            for idx, dist in zip(indices[0], distances[0])
        ]
        
        return results
