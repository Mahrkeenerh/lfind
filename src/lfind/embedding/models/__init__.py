from .embedding_model import EmbeddingModel
from .sentence_transformers import SentenceTransformerModel
from .openai_embeddings import OpenAIEmbeddingModel

__all__ = [
    'EmbeddingModel',
    'SentenceTransformerModel',
    'OpenAIEmbeddingModel',
]

def get_model(provider: str, model_name: str = None) -> EmbeddingModel:
    """Factory function to get the appropriate embedding model.
    
    Args:
        provider: Model provider ('openai', 'sentence-transformers')
        model_name: Specific model name
        
    Returns:
        An embedding model instance
    """
    provider = provider.lower()
    
    if provider == 'openai':
        model_name = model_name or "text-embedding-3-small"
        return OpenAIEmbeddingModel(model_name=model_name)
    elif provider in ('sentence-transformers', 'st', 'huggingface', 'hf'):
        model_name = model_name or "all-MiniLM-L6-v2"
        return SentenceTransformerModel(model_name=model_name)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
