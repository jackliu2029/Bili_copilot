"""Tests for bili_copilot.bilibili_client.

All tests use fake sessions and fake responses; no real network requests are made.
"""

import pytest
import requests

from bili_copilot.bilibili_client import (
    BilibiliApiError,
    BilibiliClient,
    BilibiliNetworkError,
    build_video_meta_from_view,
    extract_subtitle_tracks,
    is_subtitle_login_required,
)
from bili_copilot.models import SubtitleTrack


class FakeResponse:
    """A fake requests.Response for unit tests."""

    def __init__(self, json_data, status_code=200, raise_error=None):
        self._json = json_data
        self.status_code = status_code
        self._raise_error = raise_error

    def raise_for_status(self):
        if self._raise_error is not None:
            raise self._raise_error

    def json(self):
        return self._json


class FakeSession:
    """A fake requests.Session that records calls and returns a fixed response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        return self.response


def _sample_view_data():
    return {
        "bvid": "BV1xx411c7mD",
        "aid": 12345,
        "title": "测试视频",
        "desc": "测试简介",
        "duration": 120,
        "owner": {"name": "测试UP", "mid": 999},
        "pages": [
            {"cid": 111111, "page": 1, "part": "第一P", "duration": 60},
            {"cid": 222222, "page": 2, "part": "第二P", "duration": 60},
        ],
    }


def test_fetch_video_view_returns_data():
    response = FakeResponse({"code": 0, "message": "0", "data": _sample_view_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    data = client.fetch_video_view("BV1xx411c7mD")

    assert data["bvid"] == "BV1xx411c7mD"
    assert data["aid"] == 12345


def test_fetch_video_view_raises_api_error_on_nonzero_code():
    response = FakeResponse({"code": -404, "message": "啥都木有"})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    with pytest.raises(BilibiliApiError) as exc_info:
        client.fetch_video_view("BV1xx411c7mD")

    assert "code=-404" in str(exc_info.value)


def test_fetch_video_view_raises_network_error_on_http_failure():
    response = FakeResponse(
        {},
        raise_error=requests.RequestException("Connection refused"),
    )
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    with pytest.raises(BilibiliNetworkError):
        client.fetch_video_view("BV1xx411c7mD")


def test_fetch_video_view_passes_timeout_to_session():
    response = FakeResponse({"code": 0, "data": _sample_view_data()})
    session = FakeSession(response)
    client = BilibiliClient(timeout=7.5, session=session)

    client.fetch_video_view("BV1xx411c7mD")

    assert len(session.calls) == 1
    assert session.calls[0]["kwargs"]["timeout"] == 7.5


def test_fetch_video_view_passes_headers_without_cookies():
    response = FakeResponse({"code": 0, "data": _sample_view_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    client.fetch_video_view("BV1xx411c7mD")

    headers = session.calls[0]["kwargs"]["headers"]
    assert headers["Referer"] == "https://www.bilibili.com/"
    assert "Cookie" not in headers
    assert "cookie" not in {k.lower() for k in headers}


_FAKE_COOKIE_HEADER = "SESSDATA=fake_session_value; bili_jct=fake_csrf_value"


def test_fetch_video_view_passes_cookie_header_when_provided():
    response = FakeResponse({"code": 0, "data": _sample_view_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session, cookie_header=_FAKE_COOKIE_HEADER)

    client.fetch_video_view("BV1xx411c7mD")

    headers = session.calls[0]["kwargs"]["headers"]
    assert headers["Cookie"] == _FAKE_COOKIE_HEADER


def test_fetch_player_info_passes_cookie_header_when_provided():
    response = FakeResponse({"code": 0, "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session, cookie_header=_FAKE_COOKIE_HEADER)

    client.fetch_player_info(aid=12345, cid=111111)

    headers = session.calls[0]["kwargs"]["headers"]
    assert headers["Cookie"] == _FAKE_COOKIE_HEADER


def test_exception_messages_do_not_include_cookie_value():
    response = FakeResponse(
        {},
        raise_error=requests.RequestException("Connection refused"),
    )
    session = FakeSession(response)
    client = BilibiliClient(session=session, cookie_header=_FAKE_COOKIE_HEADER)

    with pytest.raises(BilibiliNetworkError) as exc_info:
        client.fetch_video_view("BV1xx411c7mD")

    assert "fake_session_value" not in str(exc_info.value)
    assert "fake_csrf_value" not in str(exc_info.value)


def test_fetch_video_view_raises_api_error_when_data_missing():
    response = FakeResponse({"code": 0, "message": "0"})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    with pytest.raises(BilibiliApiError) as exc_info:
        client.fetch_video_view("BV1xx411c7mD")

    assert "Missing data" in str(exc_info.value)


def test_build_video_meta_from_view_extracts_basic_fields():
    video, pages = build_video_meta_from_view(
        input_url="https://www.bilibili.com/video/BV1xx411c7mD",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD",
        bvid="BV1xx411c7mD",
        page=1,
        view_data=_sample_view_data(),
    )

    assert video.platform == "bilibili"
    assert video.bvid == "BV1xx411c7mD"
    assert video.aid == 12345
    assert video.title == "测试视频"
    assert video.owner_name == "测试UP"
    assert video.owner_mid == 999
    assert video.duration == 120
    assert video.desc == "测试简介"
    assert video.page == 1
    assert video.cid == 111111
    assert video.part_title == "第一P"


def test_build_video_meta_from_view_generates_pages():
    _, pages = build_video_meta_from_view(
        input_url="BV1xx411c7mD",
        canonical_url=None,
        bvid="BV1xx411c7mD",
        page=1,
        view_data=_sample_view_data(),
    )

    assert len(pages) == 2
    assert pages[0].page == 1
    assert pages[0].cid == 111111
    assert pages[1].page == 2
    assert pages[1].cid == 222222


def test_build_video_meta_from_view_selects_page_2():
    video, _ = build_video_meta_from_view(
        input_url="BV1xx411c7mD?p=2",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD?p=2",
        bvid="BV1xx411c7mD",
        page=2,
        view_data=_sample_view_data(),
    )

    assert video.page == 2
    assert video.cid == 222222
    assert video.part_title == "第二P"


def test_build_video_meta_from_view_defaults_to_page_1_when_out_of_range():
    video, _ = build_video_meta_from_view(
        input_url="BV1xx411c7mD?p=99",
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD?p=99",
        bvid="BV1xx411c7mD",
        page=99,
        view_data=_sample_view_data(),
    )

    assert video.page == 1
    assert video.cid == 111111
    assert video.part_title == "第一P"


def test_fetch_video_meta_uses_fetch_video_view_and_builder():
    response = FakeResponse({"code": 0, "message": "0", "data": _sample_view_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    video, pages = client.fetch_video_meta(
        input_url="https://www.bilibili.com/video/BV1xx411c7mD?p=2",
        bvid="BV1xx411c7mD",
        page=2,
        canonical_url="https://www.bilibili.com/video/BV1xx411c7mD?p=2",
    )

    assert video.title == "测试视频"
    assert video.page == 2
    assert len(pages) == 2


def _sample_player_data():
    return {
        "subtitle": {
            "subtitles": [
                {
                    "id": 1,
                    "lan": "zh-CN",
                    "lan_doc": "中文（中国）",
                    "subtitle_url": "https://example.com/sub1.json",
                }
            ]
        }
    }


def test_fetch_player_info_returns_data():
    response = FakeResponse({"code": 0, "message": "0", "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    data = client.fetch_player_info(aid=12345, cid=111111, bvid="BV1xx411c7mD")

    assert "subtitle" in data
    assert session.calls[0]["kwargs"]["params"]["aid"] == 12345
    assert session.calls[0]["kwargs"]["params"]["cid"] == 111111
    assert session.calls[0]["kwargs"]["params"]["bvid"] == "BV1xx411c7mD"


def test_fetch_player_info_raises_api_error_on_nonzero_code():
    response = FakeResponse({"code": -400, "message": "请求错误"})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    with pytest.raises(BilibiliApiError) as exc_info:
        client.fetch_player_info(aid=12345, cid=111111)

    assert "code=-400" in str(exc_info.value)


def test_fetch_player_info_raises_network_error_on_http_failure():
    response = FakeResponse(
        {},
        raise_error=requests.RequestException("Connection refused"),
    )
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    with pytest.raises(BilibiliNetworkError):
        client.fetch_player_info(aid=12345, cid=111111)


def test_fetch_player_info_passes_timeout_to_session():
    response = FakeResponse({"code": 0, "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(timeout=5.0, session=session)

    client.fetch_player_info(aid=12345, cid=111111)

    assert session.calls[0]["kwargs"]["timeout"] == 5.0


def test_fetch_player_info_passes_headers_without_cookies():
    response = FakeResponse({"code": 0, "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    client.fetch_player_info(aid=12345, cid=111111)

    headers = session.calls[0]["kwargs"]["headers"]
    assert headers["Referer"] == "https://www.bilibili.com/"
    assert "Cookie" not in headers
    assert "cookie" not in {k.lower() for k in headers}


def test_extract_subtitle_tracks_parses_standard_track():
    tracks = extract_subtitle_tracks(_sample_player_data())

    assert len(tracks) == 1
    track = tracks[0]
    assert track.id == "1"
    assert track.lan == "zh-CN"
    assert track.lan_doc == "中文（中国）"
    assert track.subtitle_url == "https://example.com/sub1.json"
    assert track.is_ai is False
    assert track.selected is False


def test_extract_subtitle_tracks_parses_multiple_tracks():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": 1,
                    "lan": "zh-CN",
                    "lan_doc": "中文",
                    "subtitle_url": "https://example.com/sub1.json",
                },
                {
                    "id": 2,
                    "lan": "zh-Hans",
                    "lan_doc": "中文（简体）",
                    "subtitle_url": "https://example.com/sub2.json",
                },
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)

    assert len(tracks) == 2
    assert tracks[0].lan == "zh-CN"
    assert tracks[1].lan == "zh-Hans"


def test_extract_subtitle_tracks_normalizes_protocol_relative_url():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": 3,
                    "lan": "zh-CN",
                    "lan_doc": "中文",
                    "subtitle_url": "//example.com/sub3.json",
                }
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)

    assert tracks[0].subtitle_url == "https://example.com/sub3.json"


def test_extract_subtitle_tracks_returns_empty_when_subtitle_missing():
    assert extract_subtitle_tracks({}) == []


def test_extract_subtitle_tracks_returns_empty_when_subtitles_empty():
    assert extract_subtitle_tracks({"subtitle": {"subtitles": []}}) == []


def test_fetch_subtitle_tracks_returns_tracks():
    response = FakeResponse({"code": 0, "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    tracks = client.fetch_subtitle_tracks(aid=12345, cid=111111)

    assert len(tracks) == 1
    assert tracks[0].lan == "zh-CN"


def test_extract_subtitle_tracks_detects_ai_from_lan_doc():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": 4,
                    "lan": "zh-CN",
                    "lan_doc": "中文（自动生成）",
                    "subtitle_url": "https://example.com/sub4.json",
                },
                {
                    "id": 5,
                    "lan": "zh-CN",
                    "lan_doc": "中文 AI 字幕",
                    "subtitle_url": "https://example.com/sub5.json",
                },
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)

    assert tracks[0].is_ai is True
    assert tracks[1].is_ai is True


def test_extract_subtitle_tracks_detects_non_ai():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": 6,
                    "lan": "zh-CN",
                    "lan_doc": "中文",
                    "subtitle_url": "https://example.com/sub6.json",
                }
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)

    assert tracks[0].is_ai is False


def test_fetch_subtitle_tracks_does_not_download_content():
    response = FakeResponse({"code": 0, "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    client.fetch_subtitle_tracks(aid=12345, cid=111111)

    # Only one API call should be made: to the player info endpoint.
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == BilibiliClient.PLAYER_V2_URL
def test_is_subtitle_login_required_true():
    assert is_subtitle_login_required({"need_login_subtitle": True}) is True


def test_is_subtitle_login_required_false():
    assert is_subtitle_login_required({"need_login_subtitle": False}) is False


def test_is_subtitle_login_required_missing():
    assert is_subtitle_login_required({}) is False


def test_fetch_subtitle_tracks_with_status_returns_tracks_and_login_flag():
    response = FakeResponse({"code": 0, "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    tracks, need_login = client.fetch_subtitle_tracks_with_status(
        aid=12345, cid=111111
    )

    assert len(tracks) == 1
    assert need_login is False


def test_fetch_subtitle_tracks_with_status_detects_login_required():
    player_data = _sample_player_data()
    player_data["need_login_subtitle"] = True
    response = FakeResponse({"code": 0, "data": player_data})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    tracks, need_login = client.fetch_subtitle_tracks_with_status(
        aid=12345, cid=111111
    )

    assert len(tracks) == 1
    assert need_login is True


def test_fetch_subtitle_tracks_with_status_does_not_download_content():
    response = FakeResponse({"code": 0, "data": _sample_player_data()})
    session = FakeSession(response)
    client = BilibiliClient(session=session)

    client.fetch_subtitle_tracks_with_status(aid=12345, cid=111111)

    assert len(session.calls) == 1
    assert session.calls[0]["url"] == BilibiliClient.PLAYER_V2_URL


def test_extract_subtitle_tracks_detects_ai_from_lan_ai_zh():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": 1,
                    "lan": "ai-zh",
                    "lan_doc": "中文",
                    "subtitle_url": "https://example.com/sub.json",
                }
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)
    assert tracks[0].is_ai is True


def test_extract_subtitle_tracks_detects_ai_from_lan_ai_en():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": 1,
                    "lan": "ai-en",
                    "lan_doc": "English",
                    "subtitle_url": "https://example.com/sub.json",
                }
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)
    assert tracks[0].is_ai is True


def test_extract_subtitle_tracks_detects_ai_from_id_ai_zh():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": "ai-zh",
                    "lan": "zh-CN",
                    "lan_doc": "中文",
                    "subtitle_url": "https://example.com/sub.json",
                }
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)
    assert tracks[0].is_ai is True


def test_extract_subtitle_tracks_keeps_zh_cn_human_without_ai_markers():
    player_data = {
        "subtitle": {
            "subtitles": [
                {
                    "id": 1,
                    "lan": "zh-CN",
                    "lan_doc": "中文（中国）",
                    "subtitle_url": "https://example.com/sub.json",
                }
            ]
        }
    }
    tracks = extract_subtitle_tracks(player_data)
    assert tracks[0].is_ai is False


def test_fetch_subtitle_tracks_with_status_retries_when_all_urls_missing():
    # First two calls return tracks without URLs; third call returns URL.
    response1 = FakeResponse(
        {
            "code": 0,
            "data": {
                "subtitle": {
                    "subtitles": [
                        {
                            "id": 1,
                            "lan": "ai-zh",
                            "lan_doc": "中文",
                            "subtitle_url": "",
                        }
                    ]
                }
            },
        }
    )
    response2 = FakeResponse(
        {
            "code": 0,
            "data": {
                "subtitle": {
                    "subtitles": [
                        {
                            "id": 1,
                            "lan": "ai-zh",
                            "lan_doc": "中文",
                            "subtitle_url": "",
                        }
                    ]
                }
            },
        }
    )
    response3 = FakeResponse(
        {
            "code": 0,
            "data": {
                "subtitle": {
                    "subtitles": [
                        {
                            "id": 1,
                            "lan": "ai-zh",
                            "lan_doc": "中文",
                            "subtitle_url": "https://example.com/sub.json",
                        }
                    ]
                }
            },
        }
    )

    class MultiResponseSession:
        def __init__(self, responses):
            self.responses = responses
            self.index = 0
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append({"url": url, "kwargs": kwargs})
            response = self.responses[self.index]
            self.index = min(self.index + 1, len(self.responses) - 1)
            return response

    session = MultiResponseSession([response1, response2, response3])
    client = BilibiliClient(
        session=session,
        subtitle_retry_count=2,
        subtitle_retry_delay=0.0,
    )

    tracks, _ = client.fetch_subtitle_tracks_with_status(aid=12345, cid=111111)

    assert len(tracks) == 1
    assert tracks[0].subtitle_url == "https://example.com/sub.json"
    assert len(session.calls) == 3


def test_fetch_subtitle_tracks_with_status_gives_up_after_retries():
    response = FakeResponse(
        {
            "code": 0,
            "data": {
                "subtitle": {
                    "subtitles": [
                        {
                            "id": 1,
                            "lan": "ai-zh",
                            "lan_doc": "中文",
                            "subtitle_url": "",
                        }
                    ]
                }
            },
        }
    )
    session = FakeSession(response)
    client = BilibiliClient(
        session=session,
        subtitle_retry_count=2,
        subtitle_retry_delay=0.0,
    )

    tracks, _ = client.fetch_subtitle_tracks_with_status(aid=12345, cid=111111)

    assert len(tracks) == 1
    assert tracks[0].subtitle_url is None
    assert len(session.calls) == 3


def test_fetch_subtitle_tracks_with_status_no_retry_when_tracks_empty():
    response = FakeResponse({"code": 0, "data": {"subtitle": {"subtitles": []}}})
    session = FakeSession(response)
    client = BilibiliClient(
        session=session,
        subtitle_retry_count=2,
        subtitle_retry_delay=0.0,
    )

    tracks, _ = client.fetch_subtitle_tracks_with_status(aid=12345, cid=111111)

    assert tracks == []
    assert len(session.calls) == 1
