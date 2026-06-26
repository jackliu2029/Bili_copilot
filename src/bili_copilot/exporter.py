"""Local export layer for Bili_copilot extraction results.

This module writes JSON, TXT, and Markdown files to disk. It does not make
any network requests and does not depend on the Bilibili API.
"""

import json
from pathlib import Path

from bili_copilot.models import (
    ExtractionResult,
    VideoMeta,
    dataclass_to_dict,
)
from bili_copilot.utils import format_timestamp_range, sanitize_filename


def build_output_dir(base_dir: Path, video: VideoMeta) -> Path:
    """Build and return the output directory path for a video.

    Format: ``{base_dir}/{bvid}_{sanitized_title}``
    """
    safe_title = sanitize_filename(video.title)
    dir_name = f"{video.bvid}_{safe_title}"
    return base_dir / dir_name


def export_result(result: ExtractionResult, output_base: Path) -> Path:
    """Export an extraction result to the filesystem.

    Creates the output directory and writes the standard set of files:

    - 00_video_meta.json
    - 01_pages.json
    - 02_subtitle_tracks.json
    - 03_transcript_raw.json
    - 04_transcript_with_timestamps.txt
    - 05_transcript_plain.txt
    - 06_content_for_ai.md

    Returns the path to the created output directory.
    """
    output_dir = build_output_dir(output_base, result.video)
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_json(output_dir / "00_video_meta.json", dataclass_to_dict(result.video))
    _write_json(output_dir / "01_pages.json", dataclass_to_dict(result.pages))
    _write_json(
        output_dir / "02_subtitle_tracks.json", dataclass_to_dict(result.subtitle_tracks)
    )
    _write_json(output_dir / "03_transcript_raw.json", dataclass_to_dict(result))

    _write_transcript_with_timestamps(output_dir / "04_transcript_with_timestamps.txt", result)
    _write_transcript_plain(output_dir / "05_transcript_plain.txt", result)
    _write_content_for_ai(output_dir / "06_content_for_ai.md", result)

    return output_dir


def _write_json(path: Path, data: object) -> None:
    """Write data to a JSON file with UTF-8 and indentation."""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_transcript_with_timestamps(path: Path, result: ExtractionResult) -> None:
    """Write segments with timestamp ranges, one per line."""
    lines = [
        f"[{format_timestamp_range(seg.start, seg.end)}] {seg.text}"
        for seg in result.segments
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_transcript_plain(path: Path, result: ExtractionResult) -> None:
    """Write plain segment text, one per line."""
    lines = [seg.text for seg in result.segments]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_content_for_ai(path: Path, result: ExtractionResult) -> None:
    """Write a Markdown content package intended for external AI analysis."""
    video = result.video
    selected = result.selected_track

    lines = [
        "# B站视频原始内容包",
        "",
        "## 视频信息",
        "",
        f"- 标题：{video.title}",
        f"- BV号：{video.bvid}",
        f"- 平台：{video.platform}",
        f"- 输入链接：{video.input_url}",
        f"- 规范链接：{video.canonical_url or 'N/A'}",
        f"- 当前分P：{video.page}",
        f"- 分P标题：{video.part_title or 'N/A'}",
        f"- UP主：{video.owner_name or 'N/A'}",
        f"- 时长：{video.duration if video.duration is not None else 'N/A'} 秒",
        f"- 状态：{result.status}",
        f"- 说明：{result.message or 'N/A'}",
        "",
        "## 字幕说明",
        "",
    ]

    if selected is None:
        lines.append("未选择字幕轨。")
    else:
        lines.append(f"- 选中字幕：{selected.lan_doc}（{selected.lan}）")
        lines.append(f"- 是否 AI 生成：{'是' if selected.is_ai else '否'}")
        lines.append(f"- 字幕轨 ID：{selected.id or 'N/A'}")

    lines.extend(
        [
            "",
            "## 字幕原文（带时间戳）",
            "",
        ]
    )
    for seg in result.segments:
        lines.append(f"[{format_timestamp_range(seg.start, seg.end)}] {seg.text}")

    lines.extend(
        [
            "",
            "## 给外部 AI 的使用说明",
            "",
            "请基于以下原始内容分析，不要编造视频中没有的信息；如需引用内容，尽量引用时间戳。",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")
