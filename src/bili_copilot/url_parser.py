"""URL parser for Bilibili inputs.

This module performs only local string/regex parsing.
It does not make any network requests.
"""

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


BV_PATTERN = re.compile(r"^BV[0-9A-Za-z]{10}$")


@dataclass(frozen=True)
class ParsedBiliInput:
    """Result of parsing a user-supplied Bilibili input."""

    raw_input: str
    input_type: str
    bvid: str | None
    page: int
    canonical_url: str | None
    needs_short_url_resolution: bool


def _extract_page(query: str) -> int:
    """Extract the page number from a query string.

    Returns 1 if the parameter is missing, non-numeric, zero, or negative.
    """
    params = parse_qs(query)
    p_values = params.get("p", [])
    if not p_values:
        return 1
    try:
        page = int(p_values[0])
    except ValueError:
        return 1
    if page <= 0:
        return 1
    return page


def _canonical_url(bvid: str, page: int) -> str:
    """Build a canonical Bilibili video URL from a BV id and page number."""
    if page == 1:
        return f"https://www.bilibili.com/video/{bvid}"
    return f"https://www.bilibili.com/video/{bvid}?p={page}"


def _invalid_result(raw_input: str) -> ParsedBiliInput:
    """Return a standardized invalid parse result."""
    return ParsedBiliInput(
        raw_input=raw_input,
        input_type="invalid",
        bvid=None,
        page=1,
        canonical_url=None,
        needs_short_url_resolution=False,
    )


def parse_bili_input(raw_input: str) -> ParsedBiliInput:
    """Parse a user-supplied Bilibili input without network access.

    Supported inputs:
    - Standard Bilibili video URLs: https://www.bilibili.com/video/BVxxxxx
    - URLs with a page parameter:   https://www.bilibili.com/video/BVxxxxx?p=2
    - Raw BV ids:                   BVxxxxx
    - b23.tv short links:           https://b23.tv/xxxxx

    Invalid inputs (empty strings, non-Bilibili URLs, Bilibili URLs without a
    BV id) are returned with ``input_type == "invalid"``.
    """
    text = raw_input.strip()

    if not text:
        return _invalid_result(raw_input)

    lowered = text.lower()
    if lowered.startswith("https://b23.tv/") or lowered.startswith("http://b23.tv/"):
        return ParsedBiliInput(
            raw_input=raw_input,
            input_type="b23_short_url",
            bvid=None,
            page=1,
            canonical_url=None,
            needs_short_url_resolution=True,
        )

    if BV_PATTERN.match(text):
        bvid = text
        return ParsedBiliInput(
            raw_input=raw_input,
            input_type="bvid",
            bvid=bvid,
            page=1,
            canonical_url=_canonical_url(bvid, 1),
            needs_short_url_resolution=False,
        )

    parsed = urlparse(text)
    netloc = parsed.netloc.lower()
    if netloc not in ("bilibili.com", "www.bilibili.com"):
        return _invalid_result(raw_input)

    match = re.search(r"/video/(BV[0-9A-Za-z]{10})/?", parsed.path)
    if not match:
        return _invalid_result(raw_input)

    bvid = match.group(1)
    page = _extract_page(parsed.query)
    return ParsedBiliInput(
        raw_input=raw_input,
        input_type="bilibili_url",
        bvid=bvid,
        page=page,
        canonical_url=_canonical_url(bvid, page),
        needs_short_url_resolution=False,
    )
