"""PoC main pipeline orchestration.

Connects URL parsing, video metadata fetching, subtitle track selection,
subtitle content fetching, and export into a single callable flow.
"""

from pathlib import Path

from bili_copilot.bilibili_client import BilibiliClient
from bili_copilot.exporter import export_result
from bili_copilot.models import ExtractionResult, TranscriptSegment, VideoMeta
from bili_copilot.subtitle_fetcher import SubtitleFetcher
from bili_copilot.subtitle_selector import (
    mark_selected_track,
    select_primary_subtitle_track,
)
from bili_copilot.url_parser import parse_bili_input


class PipelineError(Exception):
    """Raised when the extraction pipeline cannot proceed."""


def run_pipeline(
    input_url: str,
    output_base: Path,
    client: object | None = None,
    subtitle_fetcher: object | None = None,
    cookie_header: str | None = None,
) -> Path:
    """Run the full Bili_copilot extraction pipeline for a single input URL.

    Args:
        input_url: A Bilibili URL, raw BV id, or b23.tv short link.
        output_base: Directory under which the per-video output folder will be
            created.
        client: A Bilibili client with ``fetch_video_meta`` and
            ``fetch_subtitle_tracks`` methods. Defaults to ``BilibiliClient``.
        subtitle_fetcher: A fetcher with a ``fetch_segments`` method. Defaults
            to ``SubtitleFetcher``.
        cookie_header: Optional HTTP ``Cookie`` header string for authenticated
            requests. Never logged or exported.

    Returns:
        The path to the created output directory.

    Raises:
        PipelineError: If the input cannot be parsed, the requested page lacks
            required identifiers, or a short link cannot be resolved locally.
    """
    parsed = parse_bili_input(input_url)

    if parsed.input_type == "invalid":
        raise PipelineError(f"Invalid Bilibili input: {input_url!r}")

    if parsed.needs_short_url_resolution:
        raise PipelineError(
            "b23.tv short links require network resolution, "
            "which is not implemented in the current PoC stage."
        )

    if parsed.bvid is None:
        raise PipelineError(f"Could not determine BV id from input: {input_url!r}")

    bvid = parsed.bvid
    page = parsed.page
    canonical_url = parsed.canonical_url

    pipeline_client = client if client is not None else BilibiliClient(
        cookie_header=cookie_header
    )
    video_meta, pages = pipeline_client.fetch_video_meta(
        input_url=input_url,
        bvid=bvid,
        page=page,
        canonical_url=canonical_url,
    )

    if video_meta.aid is None or video_meta.cid is None:
        raise PipelineError(
            f"Missing aid or cid for {bvid}; cannot fetch subtitle tracks."
        )

    if hasattr(pipeline_client, "fetch_subtitle_tracks_with_status"):
        subtitle_tracks, need_login_subtitle = (
            pipeline_client.fetch_subtitle_tracks_with_status(
                aid=video_meta.aid,
                cid=video_meta.cid,
                bvid=bvid,
            )
        )
    else:
        subtitle_tracks = pipeline_client.fetch_subtitle_tracks(
            aid=video_meta.aid,
            cid=video_meta.cid,
            bvid=bvid,
        )
        need_login_subtitle = False

    selected_track = select_primary_subtitle_track(subtitle_tracks)
    marked_tracks = mark_selected_track(subtitle_tracks, selected_track)

    segments: list[TranscriptSegment] = []
    status = "no_subtitle"
    message: str | None = None

    if selected_track is None:
        if need_login_subtitle:
            status = "login_required"
            message = (
                "Subtitle tracks are gated by login state. "
                "Current public (no-Cookie) request cannot retrieve subtitle tracks."
            )
        else:
            message = "No subtitle tracks available for this video."
    elif not selected_track.subtitle_url:
        message = (
            "Subtitle tracks are available but the selected track has no "
            "downloadable URL. This may be a transient API response."
        )
        status = "subtitle_url_missing"
    else:
        fetcher = (
            subtitle_fetcher
            if subtitle_fetcher is not None
            else SubtitleFetcher(cookie_header=cookie_header)
        )
        segments = fetcher.fetch_segments(selected_track.subtitle_url)
        status = "success" if segments else "empty_subtitle"
        if not segments:
            message = "Selected subtitle track returned no segments."

    result = ExtractionResult(
        status=status,
        video=video_meta,
        pages=pages,
        subtitle_tracks=marked_tracks,
        selected_track=selected_track,
        segments=segments,
        message=message,
    )

    return export_result(result, output_base)
