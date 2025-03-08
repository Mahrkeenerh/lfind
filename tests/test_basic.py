# tests/test_basic.py
import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add src directory to path to import lfind
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lfind.db_manager import DatabaseManager
from src.lfind.config import load_config

class TestBasicFunctionality(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a temporary database file
        self.db_path = os.path.join(self.test_dir, "test_metadata.db")
        self.db = DatabaseManager(self.db_path)
        
        # Create some test files
        self.create_test_files()
        
    def tearDown(self):
        """Clean up test environment"""
        # Close database connection
        self.db.close()
        
        # Remove temporary directory and all its contents
        shutil.rmtree(self.test_dir)
    
    def create_test_files(self):
        """Create test files in the temporary directory"""
        # Create directory structure
        os.makedirs(os.path.join(self.test_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "src"), exist_ok=True)
        
        # Create test files with content
        files = [
            ("test.txt", "This is a test file for searching."),
            ("docs/document.md", "# Documentation\nThis is a documentation file."),
            ("src/code.py", "def test():\n    print('Hello, world!')")
        ]
        
        for rel_path, content in files:
            file_path = os.path.join(self.test_dir, rel_path)
            with open(file_path, "w") as f:
                f.write(content)
    
    def test_database_initialization(self):
        """Test that database is properly initialized"""
        # This just checks if the database was created
        self.assertTrue(os.path.exists(self.db_path))
    
    def test_touch_file(self):
        """Test touch_file functionality"""
        # Create file data for a test file
        file_path = os.path.join(self.test_dir, "test.txt")
        file_data = {
            "name": "test.txt",
            "absolute_path": file_path,
            "type": "file"
        }
        
        # Touch file should return True for a new file
        result = self.db.touch_file(file_data)
        self.assertTrue(result)
        
        # Touch file should return False for an unchanged file
        result = self.db.touch_file(file_data)
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
