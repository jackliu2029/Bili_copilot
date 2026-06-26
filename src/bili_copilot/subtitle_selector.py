"""Subtitle track selection strategy.

This module implements pure-local heuristics for choosing the primary
subtitle track from a list of available tracks. It does not make network
requests and does not download subtitle content.
"""

from dataclasses import replace

from bili_copilot.models import SubtitleTrack


_SIMPLIFIED_CHINESE_MARKERS = (
    "zh-cn",
    "zh-hans",
    "简体",
    "简中",
    "简体中文",
)

_CHINESE_MARKERS = (
    "zh-tw",
    "zh-hant",
    "zh-hk",
    "繁体",
    "繁中",
    "繁體",
    "中文",
    "chinese",
)


def _track_text(track: SubtitleTrack) -> str:
    """Return a lower-case combined string of lan and lan_doc for matching."""
    return f"{track.lan} {track.lan_doc}".lower()


def is_simplified_chinese_track(track: SubtitleTrack) -> bool:
    """Return True if the track appears to be simplified Chinese."""
    text = _track_text(track)
    return any(marker in text for marker in _SIMPLIFIED_CHINESE_MARKERS)


def is_chinese_track(track: SubtitleTrack) -> bool:
    """Return True if the track appears to be any Chinese variant."""
    if is_simplified_chinese_track(track):
        return True
    if track.lan.lower().startswith("zh"):
        return True
    text = _track_text(track)
    return any(marker in text for marker in _CHINESE_MARKERS)


def select_primary_subtitle_track(
    tracks: list[SubtitleTrack],
) -> SubtitleTrack | None:
    """Select the best primary subtitle track according to project priorities.

    Priority order:
    1. Human simplified Chinese
    2. AI simplified Chinese
    3. Other human Chinese
    4. Other AI Chinese
    5. First non-AI track
    6. First any track
    7. None (empty list)

    The original ``tracks`` list and its items are not modified.
    """
    if not tracks:
        return None

    candidates = list(tracks)

    # 1. Human simplified Chinese
    for track in candidates:
        if not track.is_ai and is_simplified_chinese_track(track):
            return track

    # 2. AI simplified Chinese
    for track in candidates:
        if track.is_ai and is_simplified_chinese_track(track):
            return track

    # 3. Other human Chinese
    for track in candidates:
        if not track.is_ai and is_chinese_track(track):
            return track

    # 4. Other AI Chinese
    for track in candidates:
        if track.is_ai and is_chinese_track(track):
            return track

    # 5. First non-AI track
    for track in candidates:
        if not track.is_ai:
            return track

    # 6. First any track
    return candidates[0]


def mark_selected_track(
    tracks: list[SubtitleTrack], selected: SubtitleTrack | None
) -> list[SubtitleTrack]:
    """Return a new list with only ``selected`` marked as selected.

    The original list and track objects are not modified.
    """
    return [replace(track, selected=(track is selected)) for track in tracks]
