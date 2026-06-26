"""Subtitle JSON fetcher.

Downloads subtitle JSON from a subtitle URL and normalizes it into
``TranscriptSegment`` objects. This module only requests subtitle JSON URLs;
it does not call Bilibili video or player endpoints.
"""

from typing import Any

import requests

from bili_copilot.models import TranscriptSegment
from bili_copilot.normalizer import normalize_subtitle_json


class SubtitleFetcherError(Exception):
    """Base exception for subtitle fetcher errors."""


class SubtitleNetworkError(SubtitleFetcherError):
    """Raised when an HTTP request for a subtitle URL fails."""


class SubtitleJsonError(SubtitleFetcherError):
    """Raised when a subtitle response is not valid JSON or not a dict."""


class SubtitleFetcher:
    """Minimal fetcher for subtitle JSON content."""

    DEFAULT_TIMEOUT = 10.0
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        session: object | None = None,
        cookie_header: str | None = None,
    ):
        self.timeout = timeout
        self._session = session
        self._cookie_header = cookie_header

    @property
    def session(self) -> object:
        """Return the configured session, creating a default one if needed."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
        }
        if self._cookie_header:
            headers["Cookie"] = self._cookie_header
        return headers

    @staticmethod
    def _normalize_url(subtitle_url: str) -> str:
        """Convert protocol-relative URLs to HTTPS; otherwise return as-is."""
        if subtitle_url.startswith("//"):
            return f"https:{subtitle_url}"
        return subtitle_url

    def fetch_subtitle_json(self, subtitle_url: str) -> dict:
        """Download and return a subtitle JSON payload as a dict.

        Args:
            subtitle_url: The URL of the subtitle JSON file.

        Raises:
            SubtitleJsonError: If the URL is empty or the response is not a
                valid JSON dict.
            SubtitleNetworkError: If the HTTP request fails.
        """
        if not subtitle_url:
            raise SubtitleJsonError("Subtitle URL is empty")

        url = self._normalize_url(subtitle_url)

        try:
            response = self.session.get(
                url,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SubtitleNetworkError(
                f"Failed to fetch subtitle from {url}: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise SubtitleJsonError(
                f"Invalid JSON subtitle response from {url}: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise SubtitleJsonError(
                f"Unexpected subtitle response type from {url}: {type(payload).__name__}"
            )

        return payload

    def fetch_segments(self, subtitle_url: str) -> list[TranscriptSegment]:
        """Download a subtitle JSON URL and normalize it to segments."""
        payload = self.fetch_subtitle_json(subtitle_url)
        return normalize_subtitle_json(payload)
