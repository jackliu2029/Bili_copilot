"""Standard data models for Bili_copilot.

All models are plain dataclasses using only the Python standard library.
No pydantic, no requests, no Bilibili API logic.
"""

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


@dataclass
class PageInfo:
    """Metadata for a single page (分P) of a Bilibili video."""

    page: int
    cid: int
    part: str
    duration: float


@dataclass
class SubtitleTrack:
    """A subtitle track available for a video page."""

    id: str | None
    lan: str
    lan_doc: str
    is_ai: bool
    subtitle_url: str | None
    selected: bool = False


@dataclass
class TranscriptSegment:
    """A single subtitle cue with start/end timing and text."""

    start: float
    end: float
    text: str


@dataclass
class VideoMeta:
    """Metadata for the video being processed."""

    platform: str
    input_url: str
    canonical_url: str | None
    bvid: str
    aid: int | None
    cid: int | None
    page: int
    title: str
    part_title: str | None
    owner_name: str | None
    owner_mid: int | None
    duration: float | None
    desc: str | None


@dataclass
class ExtractionResult:
    """Complete result of an extraction attempt."""

    status: str
    video: VideoMeta
    pages: list[PageInfo]
    subtitle_tracks: list[SubtitleTrack]
    selected_track: SubtitleTrack | None
    segments: list[TranscriptSegment]
    message: str | None = None


def dataclass_to_dict(obj: Any) -> Any:
    """Convert a dataclass instance (or list of instances) to plain dicts.

    Handles nested dataclasses, lists, and ``None`` values. All primitive
    values are returned unchanged so they can be serialized with JSON.
    """
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return obj
