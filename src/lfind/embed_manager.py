import faiss
import numpy as np
import os

class EmbedManager:
    """
    A manager for handling FAISS indexing operations.
    This class creates and handles a FAISS index, allowing insertion, searching,
    and persistence of embeddings.

    Note: Deletion is not supported by default in FAISS's flat-index structures.
    """

    def __init__(self, dim: int, metric: str = 'ip'):
        """
        Initialize the EmbedManager with a specified embedding dimension and a similarity metric.
        Supported metrics: 'l2', 'ip' (dot product), 'cosine'.

        Args:
            dim (int): Dimension of the embeddings.
            metric (str): Similarity metric.
        """
        self.dim = dim
        self.metric = metric.lower()
        if self.metric == 'l2':
            self.index = faiss.IndexFlatL2(dim)
        elif self.metric in ['ip', 'cosine']:
            self.index = faiss.IndexFlatIP(dim)
        else:
            raise ValueError(f"Unsupported metric: {metric}")

    def add_embeddings(self, embeddings, ids=None):
        """
        Add embeddings to the FAISS index.
        For cosine similarity, embeddings are first normalized.

        Args:
            embeddings (array-like): A 2D array of shape (n, dim).
            ids: Not used with these indices.
        """
        embeddings = np.array(embeddings, dtype='float32')
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dim:
            raise ValueError(f"Embeddings must be a 2D array with shape (n, {self.dim})")
        if self.metric == 'cosine':
            norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norm + 1e-10)
        self.index.add(embeddings)

    def search(self, query_embedding, k=10):
        """
        Search for nearest neighbors.
        For cosine similarity, normalize the query embedding.

        Args:
            query_embedding (array-like): 1D or 2D array.
            k (int): Number of nearest neighbors.

        Returns:
            distances, indices: Results from FAISS search.
        """
        query_embedding = np.array(query_embedding, dtype='float32')
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        if query_embedding.shape[1] != self.dim:
            raise ValueError(f"Query embedding must have dimension {self.dim}")
        if self.metric == 'cosine':
            norm = np.linalg.norm(query_embedding, axis=1, keepdims=True)
            query_embedding = query_embedding / (norm + 1e-10)
        distances, indices = self.index.search(query_embedding, k)
        return distances, indices

    def save_index(self, path: str):
        """
        Save the current FAISS index to disk.

        Args:
            path (str): The file path where the index will be saved.
        """
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        faiss.write_index(self.index, path)

    def load_index(self, path: str):
        """
        Load a FAISS index from disk.

        Args:
            path (str): The file path of the saved index.
        
        Raises:
            FileNotFoundError: If the specified index file does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index file '{path}' does not exist.")
        self.index = faiss.read_index(path)

    def total_embeddings(self) -> int:
        """
        Returns the total number of embeddings stored in the index.

        Returns:
            int: Number of embeddings in the index.
        """
        return self.index.ntotal
