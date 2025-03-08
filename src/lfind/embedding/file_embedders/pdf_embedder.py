import os
import datetime
from typing import Dict, Any, Set

from ..base import FileEmbedder

class PDFEmbedder(FileEmbedder):
    """Embedder for PDF files."""
    
    @property
    def supported_extensions(self) -> Set[str]:
        return {'.pdf'}
    
    def extract_text(self, file_path: str, max_pages: int = 5) -> str:
        """Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            max_pages: Maximum number of pages to extract
            
        Returns:
            Extracted text content
        """
        try:
            # Dynamically import PyPDF2
            import PyPDF2
            
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                # Get number of pages
                num_pages = len(reader.pages)
                pages_to_read = min(max_pages, num_pages)
                
                # Extract text from pages
                for i in range(pages_to_read):
                    page = reader.pages[i]
                    text += page.extract_text() + "\n\n"
                
                # Add a note if we truncated
                if max_pages < num_pages:
                    text += f"[Note: Only the first {max_pages} pages of {num_pages} were processed]"
                    
            return text
            
        except ImportError:
            return f"[Error: PyPDF2 library not installed. Cannot extract text from PDF.]"
        except Exception as e:
            print(f"Error extracting text from PDF {file_path}: {e}")
            return f"[Error extracting text: {str(e)}]"
    
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from a PDF file."""
        stats = os.stat(file_path)
        
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                info = reader.metadata or {}
                
                # Extract metadata
                title = info.get('/Title', os.path.basename(file_path))
                author = info.get('/Author', 'Unknown')
                creator = info.get('/Creator', 'Unknown')
                producer = info.get('/Producer', 'Unknown')
                subject = info.get('/Subject', '')
                num_pages = len(reader.pages)
                
                # Get a summary from the first page
                summary = ""
                if num_pages > 0:
                    first_page_text = reader.pages[0].extract_text()
                    if first_page_text:
                        summary = first_page_text[:200] + "..." if len(first_page_text) > 200 else first_page_text
                
                return {
                    'filename': os.path.basename(file_path),
                    'title': title,
                    'author': author,
                    'creator': creator,
                    'producer': producer,
                    'subject': subject,
                    'pages': num_pages,
                    'size': stats.st_size,
                    'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                    'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    'summary': summary
                }
                
        except ImportError:
            # Fallback if PyPDF2 isn't installed
            return {
                'filename': os.path.basename(file_path),
                'size': stats.st_size,
                'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                'error': 'PyPDF2 library not installed'
            }
        except Exception as e:
            # Fallback if there's an error
            return {
                'filename': os.path.basename(file_path),
                'size': stats.st_size,
                'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                'error': str(e)
            }
