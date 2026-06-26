"""Tests for bili_copilot.pipeline.

All tests use fake client and fake subtitle fetcher; no real network requests are made.
"""

import pytest

from bili_copilot.models import PageInfo, SubtitleTrack, TranscriptSegment, VideoMeta
from bili_copilot.pipeline import PipelineError, run_pipeline


class FakeBilibiliClient:
    """Fake Bilibili client for pipeline tests."""

    def __init__(
        self, video_meta, pages, subtitle_tracks, need_login_subtitle=False
    ):
        self.video_meta = video_meta
        self.pages = pages
        self.subtitle_tracks = subtitle_tracks
        self.need_login_subtitle = need_login_subtitle
        self.fetch_video_meta_calls = []
        self.fetch_subtitle_tracks_calls = []
        self.fetch_subtitle_tracks_with_status_calls = []

    def fetch_video_meta(self, input_url, bvid, page, canonical_url=None):
        self.fetch_video_meta_calls.append(
            {
                "input_url": input_url,
                "bvid": bvid,
                "page": page,
                "canonical_url": canonical_url,
            }
        )
        return self.video_meta, self.pages

    def fetch_subtitle_tracks_with_status(self, aid, cid, bvid=None):
        self.fetch_subtitle_tracks_with_status_calls.append(
            {"aid": aid, "cid": cid, "bvid": bvid}
        )
        return self.subtitle_tracks, self.need_login_subtitle

    def fetch_subtitle_tracks(self, aid, cid, bvid=None):
        self.fetch_subtitle_tracks_calls.append(
            {"aid": aid, "cid": cid, "bvid": bvid}
        )
        return self.subtitle_tracks


class FakeSubtitleFetcher:
    """Fake subtitle fetcher for pipeline tests."""

    def __init__(self, segments):
        self.segments = segments
        self.calls = []

    def fetch_segments(self, subtitle_url):
        self.calls.append(subtitle_url)
        return self.segments


def _video_meta(aid=12345, cid=111111, page=1):
    return VideoMeta(
        platform="bilibili",
        input_url="https://www.bilibili.com/video/BV1xx411c7mD",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        aid=aid,
        cid=cid,
        page=page,
        title="测试视频",
        part_title="第一P",
        owner_name="测试UP",
        owner_mid=999,
        duration=120.0,
        desc="测试简介",
    )


def _pages():
    return [PageInfo(page=1, cid=111111, part="第一P", duration=120.0)]


def _track_with_url():
    return SubtitleTrack(
        id="1",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url="https://example.com/sub.json",
        selected=False,
    )


def _segments():
    return [
        TranscriptSegment(start=0.0, end=2.0, text="第一句字幕"),
        TranscriptSegment(start=2.0, end=4.0, text="第二句字幕"),
    ]


def test_invalid_url_raises_pipeline_error(tmp_path):
    with pytest.raises(PipelineError):
        run_pipeline("not-a-bilibili-link", tmp_path)


def test_b23_short_url_raises_pipeline_error(tmp_path):
    with pytest.raises(PipelineError) as exc_info:
        run_pipeline("https://b23.tv/abc123", tmp_path)

    assert "b23.tv" in str(exc_info.value)


def test_success_flow_exports_content(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    output_dir = run_pipeline(
        "https://www.bilibili.com/video/BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    assert output_dir.exists()
    assert (output_dir / "00_video_meta.json").exists()
    assert (output_dir / "03_transcript_raw.json").exists()
    assert (output_dir / "04_transcript_with_timestamps.txt").exists()
    assert fake_fetcher.calls == ["https://example.com/sub.json"]


def test_success_status_is_success(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "success"' in content


def test_no_subtitle_tracks_exports_no_subtitle(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    fake_client = FakeBilibiliClient(video_meta, pages, [])
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "no_subtitle"' in content


def test_selected_track_without_url_exports_subtitle_url_missing(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = SubtitleTrack(
        id="1",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url=None,
        selected=False,
    )
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    assert fake_fetcher.calls == []
    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "subtitle_url_missing"' in content


def test_empty_segments_status_is_empty_subtitle(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "empty_subtitle"' in content


def test_selected_track_is_marked(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = tmp_path / "BV1xx411c7mD_测试视频" / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"selected": true' in content


def test_pipeline_creates_expected_output_files(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

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


def test_pipeline_does_not_use_real_network(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    # All network-like calls went through the fakes.
    assert len(fake_client.fetch_video_meta_calls) == 1
    assert len(fake_client.fetch_subtitle_tracks_with_status_calls) == 1
    assert len(fake_fetcher.calls) == 1


def test_missing_aid_or_cid_raises_pipeline_error(tmp_path):
    video_meta = _video_meta(aid=None, cid=111111)
    pages = _pages()
    fake_client = FakeBilibiliClient(video_meta, pages, [])

    with pytest.raises(PipelineError):
        run_pipeline(
            "BV1xx411c7mD",
            tmp_path,
            client=fake_client,
        )


def test_page_2_passed_to_client(tmp_path):
    video_meta = _video_meta(page=2)
    pages = [
        PageInfo(page=1, cid=111111, part="第一P", duration=60.0),
        PageInfo(page=2, cid=222222, part="第二P", duration=60.0),
    ]
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    run_pipeline(
        "https://www.bilibili.com/video/BV1xx411c7mD?p=2",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    assert fake_client.fetch_video_meta_calls[0]["page"] == 2
def test_login_required_status_when_subtitles_gated(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    fake_client = FakeBilibiliClient(
        video_meta, pages, [], need_login_subtitle=True
    )
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "login_required"' in content
    assert "login" in content.lower() or "登录态" in content


def test_no_subtitle_status_when_not_gated(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    fake_client = FakeBilibiliClient(
        video_meta, pages, [], need_login_subtitle=False
    )
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "no_subtitle"' in content


def test_login_required_still_generates_all_files(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    fake_client = FakeBilibiliClient(
        video_meta, pages, [], need_login_subtitle=True
    )
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

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


def test_login_required_does_not_download_subtitles(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    fake_client = FakeBilibiliClient(
        video_meta, pages, [], need_login_subtitle=True
    )
    fake_fetcher = FakeSubtitleFetcher([])

    run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    assert fake_fetcher.calls == []


_FAKE_COOKIE_HEADER = "SESSDATA=fake_session_value; bili_jct=fake_csrf_value"


def test_pipeline_passes_cookie_header_to_default_client(monkeypatch, tmp_path):
    captured = {}

    class SpyClient:
        def __init__(self, cookie_header=None):
            captured["client_cookie_header"] = cookie_header

        def fetch_video_meta(self, input_url, bvid, page, canonical_url=None):
            return _video_meta(), _pages()

        def fetch_subtitle_tracks_with_status(self, aid, cid, bvid=None):
            return [], False

    monkeypatch.setattr(
        "bili_copilot.pipeline.BilibiliClient", SpyClient
    )

    run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        cookie_header=_FAKE_COOKIE_HEADER,
    )

    assert captured["client_cookie_header"] == _FAKE_COOKIE_HEADER


def test_pipeline_passes_cookie_header_to_default_fetcher(monkeypatch, tmp_path):
    captured = {}
    track = _track_with_url()
    segments = _segments()

    class SpyClient:
        def __init__(self, cookie_header=None):
            captured["client_cookie_header"] = cookie_header

        def fetch_video_meta(self, input_url, bvid, page, canonical_url=None):
            return _video_meta(), _pages()

        def fetch_subtitle_tracks_with_status(self, aid, cid, bvid=None):
            return [track], False

    class SpyFetcher:
        def __init__(self, cookie_header=None):
            captured["fetcher_cookie_header"] = cookie_header

        def fetch_segments(self, subtitle_url):
            return segments

    monkeypatch.setattr(
        "bili_copilot.pipeline.BilibiliClient", SpyClient
    )
    monkeypatch.setattr(
        "bili_copilot.pipeline.SubtitleFetcher", SpyFetcher
    )

    run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        cookie_header=_FAKE_COOKIE_HEADER,
    )

    assert captured["fetcher_cookie_header"] == _FAKE_COOKIE_HEADER


def test_pipeline_uses_injected_client_and_fetcher_regardless_of_cookie_header(
    tmp_path,
):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
        cookie_header=_FAKE_COOKIE_HEADER,
    )

    assert output_dir.exists()
    assert fake_fetcher.calls == ["https://example.com/sub.json"]


def test_pipeline_output_files_do_not_contain_cookie_value(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = _track_with_url()
    segments = _segments()
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher(segments)

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
        cookie_header=_FAKE_COOKIE_HEADER,
    )

    for path in output_dir.iterdir():
        content = path.read_text(encoding="utf-8")
        assert "fake_session_value" not in content
        assert "fake_csrf_value" not in content
        assert "SESSDATA" not in content
        assert "bili_jct" not in content


def test_selected_track_without_url_exports_subtitle_url_missing(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = SubtitleTrack(
        id="1",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url=None,
        selected=False,
    )
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    assert fake_fetcher.calls == []
    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "subtitle_url_missing"' in content


def test_all_tracks_without_url_exports_subtitle_url_missing(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    tracks = [
        SubtitleTrack(
            id="1",
            lan="zh-CN",
            lan_doc="中文（中国）",
            is_ai=False,
            subtitle_url=None,
            selected=False,
        ),
        SubtitleTrack(
            id="2",
            lan="ai-zh",
            lan_doc="中文",
            is_ai=True,
            subtitle_url=None,
            selected=False,
        ),
    ]
    fake_client = FakeBilibiliClient(video_meta, pages, tracks)
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert '"status": "subtitle_url_missing"' in content


def test_subtitle_url_missing_generates_all_files(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = SubtitleTrack(
        id="1",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url=None,
        selected=False,
    )
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

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


def test_subtitle_url_missing_message_does_not_leak_cookie(tmp_path):
    video_meta = _video_meta()
    pages = _pages()
    track = SubtitleTrack(
        id="1",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url=None,
        selected=False,
    )
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
        cookie_header=_FAKE_COOKIE_HEADER,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    content = raw_path.read_text(encoding="utf-8")
    assert "fake_session_value" not in content
    assert "fake_csrf_value" not in content


def test_subtitle_url_missing_message_does_not_include_url(tmp_path):
    import json

    video_meta = _video_meta()
    pages = _pages()
    track = SubtitleTrack(
        id="1",
        lan="zh-CN",
        lan_doc="中文（中国）",
        is_ai=False,
        subtitle_url=None,
        selected=False,
    )
    fake_client = FakeBilibiliClient(video_meta, pages, [track])
    fake_fetcher = FakeSubtitleFetcher([])

    output_dir = run_pipeline(
        "BV1xx411c7mD",
        tmp_path,
        client=fake_client,
        subtitle_fetcher=fake_fetcher,
    )

    raw_path = output_dir / "03_transcript_raw.json"
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    message = data.get("message", "")
    assert "downloadable URL" in message
    assert "http" not in message.lower()
    assert "subtitle_url" not in message
