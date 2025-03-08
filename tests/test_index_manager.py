# tests/test_index_manager.py
import os
import sys
import unittest
import tempfile
import shutil

# Add src directory to path to import lfind
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lfind.db_manager import DatabaseManager
from src.lfind.index_manager import update_index, should_ignore

class TestIndexManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a temporary database file
        self.db_path = os.path.join(self.test_dir, "test_metadata.db")
        
        # Create some test files and directories
        self.create_test_files()
        
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary directory and all its contents
        shutil.rmtree(self.test_dir)
    
    def create_test_files(self):
        """Create test files in the temporary directory"""
        # Create directory structure with some files to test ignore patterns
        os.makedirs(os.path.join(self.test_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, ".git"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, ".vscode"), exist_ok=True)
        
        # Create test files
        files = [
            "test.txt",
            "docs/document.md",
            ".git/HEAD",
            ".git/config",
            ".vscode/settings.json",
            ".DS_Store"  # Hidden file on macOS
        ]
        
        for rel_path in files:
            file_path = os.path.join(self.test_dir, rel_path)
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(f"Content of {rel_path}")
    
    def test_should_ignore(self):
        """Test should_ignore function"""
        # Test with various patterns
        ignore_patterns = [".*", "*.pyc", "__pycache__"]
        
        # These should be ignored
        self.assertTrue(should_ignore(".git", ignore_patterns))
        self.assertTrue(should_ignore(".vscode", ignore_patterns))
        self.assertTrue(should_ignore(".DS_Store", ignore_patterns))
        self.assertTrue(should_ignore("test.pyc", ignore_patterns))
        self.assertTrue(should_ignore("__pycache__", ignore_patterns))
        
        # These should not be ignored
        self.assertFalse(should_ignore("test.txt", ignore_patterns))
        self.assertFalse(should_ignore("docs", ignore_patterns))
    
    def test_update_index(self):
        """Test index updating"""
        # Use a more relaxed ignore pattern to include our test files
        ignore_patterns = []  # Don't ignore any files for this test
        
        # Update the index with the specific DB path
        update_index(self.test_dir, ignore_patterns, self.db_path)
        
        # Verify results by querying the database with a fresh connection
        db = DatabaseManager(self.db_path)
        try:
            files = db.get_files_by_criteria(directory=self.test_dir)
            
            # We should have at least 2 files that aren't ignored
            self.assertGreaterEqual(len(files), 2)
            
            # Get absolute paths for comparison
            file_paths = [f["absolute_path"] for f in files]
            
            # Verify specific files
            self.assertIn(os.path.join(self.test_dir, "test.txt"), file_paths)
            self.assertIn(os.path.join(self.test_dir, "docs/document.md"), file_paths)
            
            # Check for hidden files - if we've removed the ".*" pattern, they should be included
            hidden_path = os.path.join(self.test_dir, ".git/HEAD")
            if ".*" not in ignore_patterns:
                self.assertIn(hidden_path, file_paths)
            else:
                self.assertNotIn(hidden_path, file_paths)
        finally:
            # Make sure to close the database connection
            db.close()

if __name__ == "__main__":
    unittest.main()
