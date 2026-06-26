"""Tests for bili_copilot.subtitle_fetcher.

All tests use fake sessions and fake responses; no real network requests are made.
"""

import pytest
import requests

from bili_copilot.models import TranscriptSegment
from bili_copilot.subtitle_fetcher import (
    SubtitleFetcher,
    SubtitleJsonError,
    SubtitleNetworkError,
)


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


def _sample_subtitle_payload():
    return {
        "body": [
            {"from": 0.0, "to": 2.0, "content": "第一句字幕"},
            {"from": 2.0, "to": 4.0, "content": "第二句字幕"},
        ]
    }


def test_fetch_subtitle_json_returns_dict():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    payload = fetcher.fetch_subtitle_json("https://example.com/sub.json")

    assert isinstance(payload, dict)
    assert len(payload["body"]) == 2


def test_fetch_subtitle_json_raises_network_error_on_http_failure():
    response = FakeResponse(
        {},
        raise_error=requests.RequestException("Connection refused"),
    )
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    with pytest.raises(SubtitleNetworkError):
        fetcher.fetch_subtitle_json("https://example.com/sub.json")


def test_fetch_subtitle_json_raises_json_error_on_invalid_json():
    class BadResponse(FakeResponse):
        def json(self):
            raise ValueError("Not JSON")

    response = BadResponse({})
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    with pytest.raises(SubtitleJsonError):
        fetcher.fetch_subtitle_json("https://example.com/sub.json")


def test_fetch_subtitle_json_raises_json_error_on_non_dict():
    response = FakeResponse(["not", "a", "dict"])
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    with pytest.raises(SubtitleJsonError) as exc_info:
        fetcher.fetch_subtitle_json("https://example.com/sub.json")

    assert "Unexpected subtitle response type" in str(exc_info.value)


def test_fetch_subtitle_json_raises_json_error_on_empty_url():
    fetcher = SubtitleFetcher()

    with pytest.raises(SubtitleJsonError) as exc_info:
        fetcher.fetch_subtitle_json("")

    assert "empty" in str(exc_info.value).lower()


def test_fetch_subtitle_json_normalizes_protocol_relative_url():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    fetcher.fetch_subtitle_json("//example.com/sub.json")

    assert session.calls[0]["url"] == "https://example.com/sub.json"


def test_fetch_subtitle_json_passes_timeout_to_session():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(timeout=3.0, session=session)

    fetcher.fetch_subtitle_json("https://example.com/sub.json")

    assert session.calls[0]["kwargs"]["timeout"] == 3.0


def test_fetch_subtitle_json_passes_headers_without_cookies():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    fetcher.fetch_subtitle_json("https://example.com/sub.json")

    headers = session.calls[0]["kwargs"]["headers"]
    assert headers["Referer"] == "https://www.bilibili.com/"
    assert "Cookie" not in headers
    assert "cookie" not in {k.lower() for k in headers}


_FAKE_COOKIE_HEADER = "SESSDATA=fake_session_value; bili_jct=fake_csrf_value"


def test_fetch_subtitle_json_passes_cookie_header_when_provided():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session, cookie_header=_FAKE_COOKIE_HEADER)

    fetcher.fetch_subtitle_json("https://example.com/sub.json")

    headers = session.calls[0]["kwargs"]["headers"]
    assert headers["Cookie"] == _FAKE_COOKIE_HEADER


def test_fetch_segments_passes_cookie_header_when_provided():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session, cookie_header=_FAKE_COOKIE_HEADER)

    segments = fetcher.fetch_segments("https://example.com/sub.json")

    headers = session.calls[0]["kwargs"]["headers"]
    assert headers["Cookie"] == _FAKE_COOKIE_HEADER
    assert len(segments) == 2


def test_subtitle_fetcher_exception_does_not_leak_cookie_value():
    response = FakeResponse(
        {},
        raise_error=requests.RequestException("Connection refused"),
    )
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session, cookie_header=_FAKE_COOKIE_HEADER)

    with pytest.raises(SubtitleNetworkError) as exc_info:
        fetcher.fetch_subtitle_json("https://example.com/sub.json")

    assert "fake_session_value" not in str(exc_info.value)
    assert "fake_csrf_value" not in str(exc_info.value)


def test_fetch_segments_returns_transcript_segments():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    segments = fetcher.fetch_segments("https://example.com/sub.json")

    assert len(segments) == 2
    assert segments[0] == TranscriptSegment(start=0.0, end=2.0, text="第一句字幕")
    assert segments[1] == TranscriptSegment(start=2.0, end=4.0, text="第二句字幕")


def test_fetch_segments_does_not_save_files():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    fetcher.fetch_segments("https://example.com/sub.json")

    # Only one HTTP call should be made, and it should be the subtitle URL.
    assert len(session.calls) == 1


def test_fetch_subtitle_json_does_not_call_video_api():
    response = FakeResponse(_sample_subtitle_payload())
    session = FakeSession(response)
    fetcher = SubtitleFetcher(session=session)

    fetcher.fetch_subtitle_json("https://example.com/sub.json")

    url = session.calls[0]["url"]
    assert "bilibili.com" not in url or "subtitle" in url
    assert "x/web-interface/view" not in url
    assert "x/player/v2" not in url
