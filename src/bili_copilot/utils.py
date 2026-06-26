"""Utility helpers for Bili_copilot."""

import re
from pathlib import Path


_WINDOWS_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')


def get_project_root() -> Path:
    """Return the project root directory.

    This function uses pathlib and resolves relative to the current file,
    so it works across Windows, macOS, and Linux without hard-coded paths.
    """
    return Path(__file__).resolve().parent.parent.parent


def normalize_url(url: str) -> str:
    """Placeholder for URL normalization.

    In later phases this will handle b23.tv short links, BV links,
    and multi-P links. For now it returns the input unchanged.
    """
    return url


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """Sanitize a string so it can be used as a file or directory name.

    Replaces Windows illegal characters, strips whitespace, and truncates
    to ``max_length``. Preserves Chinese characters and common punctuation.
    """
    cleaned = _WINDOWS_ILLEGAL_CHARS.sub("_", name)
    cleaned = cleaned.strip()
    if not cleaned:
        return "untitled"
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned


def format_timestamp(seconds: float) -> str:
    """Format a duration in seconds as ``HH:MM:SS``.

    Examples:
        - 0     -> 00:00:00
        - 1.2   -> 00:00:01
        - 65    -> 00:01:05
        - 3661  -> 01:01:01
    """
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_timestamp_range(start: float, end: float) -> str:
    """Format a start/end timestamp pair as ``HH:MM:SS - HH:MM:SS``."""
    return f"{format_timestamp(start)} - {format_timestamp(end)}"
