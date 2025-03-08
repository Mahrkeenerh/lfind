# tests/run_all_tests.py
import unittest
import os
import sys

# Add the parent directory (project root) to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Find all test modules
loader = unittest.TestLoader()
test_suite = loader.discover(os.path.dirname(__file__), pattern="test_*.py")

# Run tests
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(test_suite)

# Exit with non-zero code if tests failed
sys.exit(not result.wasSuccessful())
