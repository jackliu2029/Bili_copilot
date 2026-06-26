"""Subtitle JSON normalization.

Converts Bilibili subtitle JSON payloads into a standardized list of
``TranscriptSegment`` objects. This module does not make network requests.
"""

from bili_copilot.models import TranscriptSegment


def _parse_float(value: object) -> float | None:
    """Parse a value as float, returning None on failure."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _parse_text(value: object) -> str | None:
    """Parse a value as a cleaned string, returning None on failure."""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def normalize_subtitle_body(body: list[dict]) -> list[TranscriptSegment]:
    """Normalize a raw subtitle body list into ``TranscriptSegment`` objects.

    Invalid items (missing fields, bad timestamps, empty text) are skipped.
    The original order is preserved.
    """
    if not isinstance(body, list):
        return []

    segments: list[TranscriptSegment] = []
    for item in body:
        if not isinstance(item, dict):
            continue

        start = _parse_float(item.get("from"))
        end = _parse_float(item.get("to"))
        text = _parse_text(item.get("content"))

        if start is None or end is None or text is None:
            continue

        segments.append(TranscriptSegment(start=start, end=end, text=text))

    return segments


def normalize_subtitle_json(payload: dict) -> list[TranscriptSegment]:
    """Normalize a subtitle JSON payload into ``TranscriptSegment`` objects.

    Expects ``payload["body"]`` to be a list of subtitle items. Returns an
    empty list if ``body`` is missing, not a list, or empty.
    """
    if not isinstance(payload, dict):
        return []

    body = payload.get("body")
    if body is None:
        return []

    return normalize_subtitle_body(body)
