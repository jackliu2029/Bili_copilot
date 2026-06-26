"""Local Cookie file reader, parser, and redaction utilities.

This module only reads user-supplied local Cookie files. It does not read
browser Cookies, make network requests, or write files. Cookie values are
never included in exception messages or log output.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Union


class CookieConfigError(Exception):
    """Base exception for Cookie configuration errors."""


class CookieFileNotFoundError(CookieConfigError):
    """Raised when the specified Cookie file does not exist or is not a file."""


class CookieFileEmptyError(CookieConfigError):
    """Raised when the Cookie file contains no valid Cookie entries."""


class CookieParseError(CookieConfigError):
    """Raised when a Cookie file line cannot be parsed."""


PathLike = Union[str, Path]


_LINE_RE = re.compile(r"^([^=]+)=(.*)$")


def parse_cookie_text(text: str) -> dict[str, str]:
    """Parse a key=value multiline Cookie text.

    Rules:
    - Empty lines are ignored.
    - Lines starting with ``#`` are treated as comments and ignored.
    - Each non-comment line must be ``key=value``.
    - Keys and values are stripped of surrounding whitespace.
    - Empty keys or values raise ``CookieParseError``.

    Cookie values are never printed or included in exception messages.
    """
    if not isinstance(text, str):
        raise CookieParseError("Cookie text must be a string")

    cookies: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _LINE_RE.match(line)
        if not match:
            raise CookieParseError(
                f"Invalid Cookie file line format (line number masked): {redact_cookie_value(line)}"
            )

        key = match.group(1).strip()
        value = match.group(2).strip()

        if not key:
            raise CookieParseError("Cookie key cannot be empty")
        if not value:
            raise CookieParseError(f"Cookie value cannot be empty for key: {key}")

        cookies[key] = value

    if not cookies:
        raise CookieFileEmptyError("Cookie file contains no valid Cookie entries")

    return cookies


def build_cookie_header(cookies: dict[str, str]) -> str:
    """Build an HTTP ``Cookie`` header string from a key/value mapping.

    Keys are sorted for deterministic output. An empty mapping raises
    ``CookieFileEmptyError``.
    """
    if not cookies:
        raise CookieFileEmptyError("Cannot build Cookie header from empty Cookie mapping")

    parts = [f"{key}={value}" for key, value in sorted(cookies.items())]
    return "; ".join(parts)


def load_cookie_header_from_file(path: PathLike) -> str:
    """Load and build a Cookie header from a local file.

    The file must contain key=value lines as defined by ``parse_cookie_text``.

    Raises:
        CookieFileNotFoundError: If ``path`` does not exist or is not a file.
        CookieFileEmptyError: If the file contains no valid entries.
        CookieParseError: If any non-comment line is malformed.
    """
    target = Path(path)

    if not target.exists():
        raise CookieFileNotFoundError(
            f"Cookie file not found: {target}"
        )
    if not target.is_file():
        raise CookieFileNotFoundError(
            f"Cookie path is not a file: {target}"
        )

    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise CookieConfigError(
            f"Failed to read Cookie file: {target}"
        ) from exc

    cookies = parse_cookie_text(text)
    return build_cookie_header(cookies)


def get_cookie_file_from_env(
    env: dict[str, str] | None = None,
) -> Path | None:
    """Return the Cookie file path from the ``BILI_COOKIE_FILE`` environment variable.

    This function only accepts a path to a Cookie file. It does not accept a raw
    Cookie string. Returns ``None`` if the variable is unset or empty.
    """
    source = env if env is not None else os.environ
    value = source.get("BILI_COOKIE_FILE", "").strip()
    if not value:
        return None
    return Path(value)


def redact_cookie_value(value: str) -> str:
    """Return a redacted representation of a single Cookie value.

    Short values are fully redacted. Longer values keep only the first four
    and last four characters with an ellipsis in between.
    """
    if not isinstance(value, str):
        value = str(value)

    if len(value) <= 8:
        return "<redacted>"

    return f"{value[:4]}...{value[-4:]}"


def redact_cookie_header(header: str) -> str:
    """Return a redacted representation of a full ``Cookie`` header string.

    Each ``name=value`` pair is transformed to ``name=<redacted>``. The original
    value is never included in the result.
    """
    if not isinstance(header, str):
        header = str(header)

    if not header.strip():
        return ""

    redacted_pairs: list[str] = []
    for pair in header.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        if "=" in pair:
            key, _ = pair.split("=", 1)
            redacted_pairs.append(f"{key.strip()}=<redacted>")
        else:
            redacted_pairs.append("<redacted>")

    return "; ".join(redacted_pairs)
