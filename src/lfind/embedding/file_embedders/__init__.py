from ..registry import registry
from .text_embedder import TextFileEmbedder
from .pdf_embedder import PDFEmbedder

__all__ = [
    'TextFileEmbedder',
    'PDFEmbedder',
]

# Register the default embedders
registry.register(TextFileEmbedder())
registry.register(PDFEmbedder())
