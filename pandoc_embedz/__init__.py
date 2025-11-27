"""pandoc-embedz: Pandoc filter for data-driven content generation"""

__version__ = '0.9.1'

from .filter import process_embedz
from .main import main

__all__ = ['process_embedz', 'main', '__version__']
