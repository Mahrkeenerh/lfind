# tests/test_search_pipeline.py
import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add src directory to path to import lfind
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lfind.db_manager import DatabaseManager
from src.lfind.search_pipeline import SearchPipeline
from src.lfind.embed_manager import EmbedManager
from src.lfind.embedding.service import EmbeddingService
from src.lfind.llm_service import LLMService

class TestSearchPipeline(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a temporary database file
        self.db_path = os.path.join(self.test_dir, "test_metadata.db")
        self.db = DatabaseManager(self.db_path)
        
        # Mock the embedding service and LLM service
        self.embedding_service = MagicMock(spec=EmbeddingService)
        self.llm_service = MagicMock(spec=LLMService)
        
        # Create basic configuration
        self.config = {
            "max_entries": 100,
            "ignore_patterns": [".*"],
            "include_empty_dirs": False,
            "cache_dir": self.test_dir,
            "cache_validity_days": 7
        }
        
        # Create the search pipeline
        self.search_pipeline = SearchPipeline(
            self.db,
            self.embedding_service,
            self.llm_service,
            self.config
        )
        
        # Create some test files and add them to the database
        self.create_test_files()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db.close()
        shutil.rmtree(self.test_dir)
    
    def create_test_files(self):
        """Create test files in the temporary directory and add to DB"""
        # Create directory structure
        os.makedirs(os.path.join(self.test_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "src"), exist_ok=True)
        
        # Define test files
        files = [
            ("test.txt", "text file", 1000),
            ("docs/document.md", "markdown document", 2000),
            ("src/code.py", "python code", 3000),
            ("src/script.js", "javascript code", 4000)
        ]
        
        # Create files and add to database
        for rel_path, content_type, size in files:
            file_path = os.path.join(self.test_dir, rel_path)
            
            # Create directory if needed
            dir_path = os.path.dirname(file_path)
            os.makedirs(dir_path, exist_ok=True)
            
            # Create file with some content
            with open(file_path, "w") as f:
                f.write(f"This is a {content_type} for testing.")
            
            # Add file to database with extension explicitly extracted
            file_name = os.path.basename(file_path)
            _, extension = os.path.splitext(file_name)
            
            file_data = {
                "name": file_name,
                "absolute_path": file_path,
                "type": "file",
                "size": size,
                "extension": extension  # Make sure extension is set correctly
            }
            self.db.touch_file(file_data)
    
    def test_filter_by_extension(self):
        """Test filtering files by extension"""
        # Test with Python files - be explicit about the extension format
        python_files = self.search_pipeline.filter_by_extension([".py"], self.test_dir)
        self.assertEqual(len(python_files), 1)
        self.assertEqual(os.path.basename(python_files[0]["absolute_path"]), "code.py")
        
        # Test with multiple extensions
        script_files = self.search_pipeline.filter_by_extension([".py", ".js"], self.test_dir)
        self.assertEqual(len(script_files), 2)
        
        # Test with text files
        text_files = self.search_pipeline.filter_by_extension([".txt"], self.test_dir)
        self.assertEqual(len(text_files), 1)
    
    @patch("src.lfind.search_pipeline.SearchPipeline.search_llm")
    def test_multi_search_with_llm(self, mock_search_llm):
        """Test multi-stage search with LLM"""
        # Configure mock to return an actual file that exists
        mock_search_llm.return_value = [
            {"name": "code.py", "absolute_path": os.path.join(self.test_dir, "src/code.py"), "id": 3, "type": "file"}
        ]
        
        # Perform search
        results = self.search_pipeline.multi_search(
            query="find python code",
            directory=self.test_dir,
            extensions=[".py", ".js", ".txt"],
            use_semantic=False,
            use_llm=True,
            top_k=5,
            filter_criteria={}  # Make sure to pass an empty dict if needed
        )
        
        # Check results
        self.assertEqual(len(results), 1)
        self.assertEqual(os.path.basename(results[0]["absolute_path"]), "code.py")
        
        # Verify LLM search was called
        mock_search_llm.assert_called_once()

if __name__ == "__main__":
    unittest.main()
