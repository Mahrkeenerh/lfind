from typing import List
import numpy as np
import os
import time

from .embedding_model import EmbeddingModel

class OpenAIEmbeddingModel(EmbeddingModel):
    """Embedding model using OpenAI's API."""
    
    # OpenAI embedding models and their dimensions
    _MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536
    }
    
    def __init__(self, model_name: str = "text-embedding-3-small"):
        """Initialize the model.
        
        Args:
            model_name: Name of the OpenAI embedding model to use
        """
        if model_name not in self._MODEL_DIMENSIONS:
            supported = ", ".join(self._MODEL_DIMENSIONS.keys())
            raise ValueError(
                f"Unsupported model: {model_name}. " 
                f"Supported models are: {supported}"
            )
            
        self.model_name = model_name
        self._dimension = self._MODEL_DIMENSIONS[model_name]
        
        try:
            import openai
            self.client = openai.OpenAI()
        except ImportError:
            raise ImportError(
                "OpenAI Python client is not installed. "
                "Install it with 'pip install openai'."
            )
    
    def get_embedding_dimension(self) -> int:
        return self._dimension
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a single text using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            print(f"Error getting OpenAI embedding: {e}")
            # Return a zero vector as fallback
            return np.zeros(self._dimension, dtype=np.float32)
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for multiple texts using OpenAI API.
        
        Handles rate limiting and batching.
        """
        results = []
        batch_size = 100  # OpenAI recommends batches of ~100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=batch
                )
                batch_embeddings = [data.embedding for data in response.data]
                results.extend(batch_embeddings)
                
                # Sleep briefly to avoid rate limits if many batches
                if i + batch_size < len(texts):
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error batch embedding texts {i} to {i+len(batch)}: {e}")
                # Add zero vectors for the failed batch
                zeros = [np.zeros(self._dimension) for _ in range(len(batch))]
                results.extend(zeros)
        
        return np.array(results, dtype=np.float32)
    
    def get_name(self) -> str:
        return self.model_name
    
    def get_provider(self) -> str:
        return "OpenAI"
