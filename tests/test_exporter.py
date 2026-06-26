"""Tests for bili_copilot.exporter."""

import json

from bili_copilot.exporter import build_output_dir, export_result
from bili_copilot.models import (
    ExtractionResult,
    PageInfo,
    SubtitleTrack,
    TranscriptSegment,
    VideoMeta,
)
from bili_copilot.utils import format_timestamp, format_timestamp_range, sanitize_filename


def test_sanitize_filename_removes_windows_illegal_chars():
    assert sanitize_filename("a/b:c*d?e\"f<g>h|i") == "a_b_c_d_e_f_g_h_i"


def test_sanitize_filename_empty_returns_untitled():
    assert sanitize_filename("   ") == "untitled"
    assert sanitize_filename("") == "untitled"


def test_sanitize_filename_truncates():
    long_name = "a" * 100
    assert len(sanitize_filename(long_name, max_length=50)) <= 50


def test_sanitize_filename_preserves_chinese():
    assert sanitize_filename("测试视频标题") == "测试视频标题"


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(1.2) == "00:00:01"
    assert format_timestamp(65) == "00:01:05"
    assert format_timestamp(3661) == "01:01:01"


def test_format_timestamp_range():
    assert format_timestamp_range(0, 5) == "00:00:00 - 00:00:05"
    assert format_timestamp_range(60, 125) == "00:01:00 - 00:02:05"


def _make_result() -> ExtractionResult:
    video = VideoMeta(
        platform="bilibili",
        input_url="https://www.bilibili.com/video/BV1xx411c7mD?p=2",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD?p=2",
        bvid="BV1xx411c7mD",
        aid=12345,
        cid=67890,
        page=2,
        title="测试:视频标题",
        part_title="第二P",
        owner_name="测试UP",
        owner_mid=999,
        duration=120.0,
        desc="测试简介",
    )
    selected = SubtitleTrack(
        id="123",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url="https://example.com/sub.json",
        selected=True,
    )
    segments = [
        TranscriptSegment(start=0.0, end=5.0, text="第一句字幕"),
        TranscriptSegment(start=5.0, end=10.0, text="第二句字幕"),
    ]
    return ExtractionResult(
        status="ok",
        video=video,
        pages=[PageInfo(page=2, cid=67890, part="第二P", duration=120.0)],
        subtitle_tracks=[selected],
        selected_track=selected,
        segments=segments,
    )


def test_build_output_dir_contains_bvid_and_title(tmp_path):
    video = VideoMeta(
        platform="bilibili",
        input_url="BV1xx411c7mD",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        aid=None,
        cid=None,
        page=1,
        title="测试视频标题",
        part_title=None,
        owner_name=None,
        owner_mid=None,
        duration=None,
        desc=None,
    )
    output_dir = build_output_dir(tmp_path, video)
    assert output_dir.name.startswith("BV1xx411c7mD_")
    assert "测试视频标题" in output_dir.name


def test_export_result_creates_six_files(tmp_path):
    result = _make_result()
    output_dir = export_result(result, tmp_path)
    assert output_dir.exists()
    expected_files = {
        "00_video_meta.json",
        "01_pages.json",
        "02_subtitle_tracks.json",
        "03_transcript_raw.json",
        "04_transcript_with_timestamps.txt",
        "05_transcript_plain.txt",
        "06_content_for_ai.md",
    }
    assert {p.name for p in output_dir.iterdir()} == expected_files


def test_video_meta_json_contains_title_and_bvid(tmp_path):
    result = _make_result()
    export_result(result, tmp_path)
    meta_path = tmp_path / "BV1xx411c7mD_测试_视频标题" / "00_video_meta.json"
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["title"] == "测试:视频标题"
    assert data["bvid"] == "BV1xx411c7mD"


def test_transcript_with_timestamps_contains_timestamps_and_text(tmp_path):
    result = _make_result()
    export_result(result, tmp_path)
    txt_path = tmp_path / "BV1xx411c7mD_测试_视频标题" / "04_transcript_with_timestamps.txt"
    content = txt_path.read_text(encoding="utf-8")
    assert "[00:00:00 - 00:00:05] 第一句字幕" in content
    assert "[00:00:05 - 00:00:10] 第二句字幕" in content


def test_transcript_plain_contains_only_text(tmp_path):
    result = _make_result()
    export_result(result, tmp_path)
    txt_path = tmp_path / "BV1xx411c7mD_测试_视频标题" / "05_transcript_plain.txt"
    content = txt_path.read_text(encoding="utf-8")
    assert content == "第一句字幕\n第二句字幕"


def test_content_for_ai_has_required_sections(tmp_path):
    result = _make_result()
    export_result(result, tmp_path)
    md_path = tmp_path / "BV1xx411c7mD_测试_视频标题" / "06_content_for_ai.md"
    content = md_path.read_text(encoding="utf-8")
    assert "# B站视频原始内容包" in content
    assert "## 给外部 AI 的使用说明" in content
    assert "请基于以下原始内容分析，不要编造视频中没有的信息" in content
