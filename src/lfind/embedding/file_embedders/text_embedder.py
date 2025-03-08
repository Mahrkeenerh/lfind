import os
import datetime
from typing import Dict, Any, Set
import numpy as np

from ..base import FileEmbedder

class TextFileEmbedder(FileEmbedder):
    """Embedder for plain text files."""
    
    @property
    def supported_extensions(self) -> Set[str]:
        return {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.csv', '.yml', 
                '.yaml', '.ini', '.cfg', '.conf', '.sh', '.bat', '.ps1', '.sql', '.log'}
    
    def extract_text(self, file_path: str, max_length: int = 10000) -> str:
        """Extract text content from a text file.
        
        Args:
            file_path: Path to the text file
            max_length: Maximum number of characters to extract
            
        Returns:
            Extracted text content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(max_length)
            return content
        except UnicodeDecodeError:
            # Try with a different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read(max_length)
                return content
            except Exception as e:
                print(f"Error reading text file {file_path}: {e}")
                return f"[Error reading file: {str(e)}]"
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")
            return f"[Error reading file: {str(e)}]"
    
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from a text file."""
        stats = os.stat(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Get the first few lines for a summary
                lines = []
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    line = line.strip()
                    if line:
                        lines.append(line)
                
                summary = '\n'.join(lines[:3]) if lines else ""
        except:
            summary = "[Error reading file summary]"
            
        return {
            'filename': os.path.basename(file_path),
            'size': stats.st_size,
            'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
            'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
            'summary': summary
        }
