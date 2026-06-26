"""Tests for bili_copilot.models."""

from bili_copilot.models import (
    ExtractionResult,
    PageInfo,
    SubtitleTrack,
    TranscriptSegment,
    VideoMeta,
    dataclass_to_dict,
)


def test_page_info_instantiation():
    page = PageInfo(page=1, cid=123456, part="P1", duration=120.0)
    assert page.page == 1
    assert page.cid == 123456


def test_subtitle_track_instantiation():
    track = SubtitleTrack(
        id="1",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url="https://example.com/sub.json",
    )
    assert track.selected is False


def test_nested_dataclass_to_dict():
    video = VideoMeta(
        platform="bilibili",
        input_url="https://www.bilibili.com/video/BV1xx411c7mD",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        aid=12345,
        cid=67890,
        page=1,
        title="测试视频",
        part_title=None,
        owner_name="测试UP",
        owner_mid=999,
        duration=120.0,
        desc="测试简介",
    )
    data = dataclass_to_dict(video)
    assert data["bvid"] == "BV1xx411c7mD"
    assert data["title"] == "测试视频"
    assert data["part_title"] is None


def test_extraction_result_with_segments():
    video = VideoMeta(
        platform="bilibili",
        input_url="https://www.bilibili.com/video/BV1xx411c7mD",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        aid=12345,
        cid=67890,
        page=1,
        title="测试视频",
        part_title=None,
        owner_name="测试UP",
        owner_mid=999,
        duration=120.0,
        desc="测试简介",
    )
    segments = [
        TranscriptSegment(start=0.0, end=5.0, text="第一句字幕"),
        TranscriptSegment(start=5.0, end=10.0, text="第二句字幕"),
    ]
    result = ExtractionResult(
        status="ok",
        video=video,
        pages=[PageInfo(page=1, cid=67890, part="P1", duration=120.0)],
        subtitle_tracks=[],
        selected_track=None,
        segments=segments,
    )
    data = dataclass_to_dict(result)
    assert data["status"] == "ok"
    assert len(data["segments"]) == 2
    assert data["segments"][0]["text"] == "第一句字幕"


def test_extraction_result_selected_track_none():
    video = VideoMeta(
        platform="bilibili",
        input_url="BV1xx411c7mD",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        aid=None,
        cid=None,
        page=1,
        title="测试视频",
        part_title=None,
        owner_name=None,
        owner_mid=None,
        duration=None,
        desc=None,
    )
    result = ExtractionResult(
        status="no_subtitle",
        video=video,
        pages=[],
        subtitle_tracks=[],
        selected_track=None,
        segments=[],
        message="No subtitle available",
    )
    data = dataclass_to_dict(result)
    assert data["selected_track"] is None
    assert data["message"] == "No subtitle available"
