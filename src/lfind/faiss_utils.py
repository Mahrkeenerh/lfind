import faiss
import numpy as np

def get_faiss_index(dim: int, metric: str = 'cosine', use_gpu: bool = True) -> faiss.Index:
    """
    Create a FAISS index with GPU support if available.
    
    Args:
        dim: Dimension of the embeddings
        metric: Distance metric ('cosine', 'l2', or 'ip')
        use_gpu: Whether to use GPU acceleration if available
        
    Returns:
        FAISS index instance
    """
    # Create the appropriate index based on the metric
    if metric == 'l2':
        index = faiss.IndexFlatL2(dim)
    elif metric == 'ip':
        index = faiss.IndexFlatIP(dim)
    elif metric == 'cosine':
        index = faiss.IndexFlatIP(dim)
    else:
        raise ValueError(f"Unsupported metric: {metric}")
    
    # Try to use GPU if requested
    if use_gpu:
        try:
            # Check if GPU resources are available
            ngpus = faiss.get_num_gpus()
            if ngpus > 0:
                gpu_resources = []
                for i in range(ngpus):
                    res = faiss.StandardGpuResources()
                    gpu_resources.append(res)
                
                # Use the first GPU for simplicity
                # For multiple GPUs, consider faiss.index_cpu_to_all_gpus
                index = faiss.index_cpu_to_gpu(gpu_resources[0], 0, index)
                print(f"FAISS index is using GPU acceleration")
        except Exception as e:
            print(f"GPU acceleration requested but failed: {e}")
            print("Falling back to CPU index")
    
    return index

def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """
    Normalize vectors to unit length for cosine similarity search.
    
    Args:
        vectors: Input vectors as numpy array
        
    Returns:
        Normalized vectors
    """
    norm = np.linalg.norm(vectors, axis=1, keepdims=True)
    # Add small epsilon to avoid division by zero
    return vectors / (norm + 1e-10)
