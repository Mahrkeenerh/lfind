# tests/test_embeddings.py
import os
import sys
import unittest
import tempfile
import numpy as np

# Add src directory to path to import lfind
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lfind.embed_manager import EmbedManager

class TestEmbeddings(unittest.TestCase):
    def test_embed_manager_basic(self):
        """Test basic functionality of EmbedManager"""
        # Create an EmbedManager with a small dimension for testing
        embed_mgr = EmbedManager(dim=4, metric='ip')
        
        # Create some test embeddings
        embeddings = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=np.float32)
        
        # Add embeddings to the index
        embed_mgr.add_embeddings(embeddings)
        
        # Verify count
        self.assertEqual(embed_mgr.total_embeddings(), 4)
        
        # Test search
        query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        distances, indices = embed_mgr.search(query, k=2)
        
        # First result should be the first embedding (identical to query)
        self.assertEqual(indices[0][0], 0)
    
    def test_save_load_index(self):
        """Test saving and loading the index"""
        # Create a temporary file for the index
        with tempfile.NamedTemporaryFile(suffix='.index', delete=False) as tmp:
            index_path = tmp.name
        
        try:
            # Create an EmbedManager and add embeddings
            embed_mgr = EmbedManager(dim=4, metric='cosine')
            
            embeddings = np.array([
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0]
            ], dtype=np.float32)
            
            embed_mgr.add_embeddings(embeddings)
            
            # Save the index
            embed_mgr.save_index(index_path)
            
            # Create a new EmbedManager and load the index
            new_embed_mgr = EmbedManager(dim=4, metric='cosine')
            new_embed_mgr.load_index(index_path)
            
            # Verify the loaded index has the same number of embeddings
            self.assertEqual(new_embed_mgr.total_embeddings(), 2)
        finally:
            # Clean up the temporary file
            if os.path.exists(index_path):
                os.unlink(index_path)
    
    def test_cosine_similarity(self):
        """Test cosine similarity in EmbedManager"""
        # Create an EmbedManager with cosine similarity
        embed_mgr = EmbedManager(dim=3, metric='cosine')
        
        # Create some test embeddings with different magnitudes
        embeddings = np.array([
            [3.0, 0.0, 0.0],  # Unit vector in x direction, but magnitude 3
            [0.0, 2.0, 0.0],  # Unit vector in y direction, but magnitude 2
            [0.0, 0.0, 1.0]   # Unit vector in z direction
        ], dtype=np.float32)
        
        # Add embeddings to the index
        embed_mgr.add_embeddings(embeddings)
        
        # Query with a vector in the x direction but with different magnitude
        query = np.array([10.0, 0.0, 0.0], dtype=np.float32)
        distances, indices = embed_mgr.search(query, k=3)
        
        # First result should be the first embedding despite different magnitude
        self.assertEqual(indices[0][0], 0)

if __name__ == "__main__":
    unittest.main()
