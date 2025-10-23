"""
AI-powered web data extractor for Naver Blogs.

This package provides tools for extracting content from dynamic web pages
using Llama 3 LLM and persisting results to Supabase.
"""

from .extractor import NaverBlogExtractor, ExtractionResult
from .database import DatabaseManager, DatabaseConfig
from .config import get_config, AppConfig

__version__ = "0.1.0"

__all__ = [
    "NaverBlogExtractor",
    "ExtractionResult",
    "DatabaseManager",
    "DatabaseConfig",
    "get_config",
    "AppConfig",
]
