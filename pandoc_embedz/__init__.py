"""pandoc-embedz: Pandoc filter for data-driven content generation"""

__version__ = '0.3.0'

from .filter import process_embedz, main

__all__ = ['process_embedz', 'main', '__version__']
