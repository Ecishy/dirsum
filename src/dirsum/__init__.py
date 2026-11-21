"""dirsum — summarize what is inside a directory tree."""

from .core import FileStat, by_extension, collect, format_bytes, per_directory, top_files

__version__ = "0.1.0"

__all__ = ["FileStat", "by_extension", "collect", "format_bytes", "per_directory", "top_files"]
