"""Bilibili public video information client.

This module fetches public video metadata and subtitle track metadata from the
Bilibili API. It does not handle login state, cookies, or download subtitle
content.
"""

import time
from typing import Any

import requests

from bili_copilot.models import PageInfo, SubtitleTrack, VideoMeta


class BilibiliClientError(Exception):
    """Base exception for Bilibili client errors."""


class BilibiliApiError(BilibiliClientError):
    """Raised when the Bilibili API returns an error code or malformed response."""


class BilibiliNetworkError(BilibiliClientError):
    """Raised when an HTTP request fails."""


class BilibiliClient:
    """Minimal client for Bilibili public video metadata."""

    API_BASE = "https://api.bilibili.com"
    PLAYER_V2_URL = "https://api.bilibili.com/x/player/v2"
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
        subtitle_retry_count: int = 3,
        subtitle_retry_delay: float = 1.0,
    ):
        self.timeout = timeout
        self._session = session
        self._cookie_header = cookie_header
        self.subtitle_retry_count = subtitle_retry_count
        self.subtitle_retry_delay = subtitle_retry_delay

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

    def fetch_video_view(self, bvid: str) -> dict[str, Any]:
        """Fetch public video view data for a given BV id.

        Endpoint: GET https://api.bilibili.com/x/web-interface/view?bvid={bvid}

        Raises:
            BilibiliNetworkError: If the HTTP request fails.
            BilibiliApiError: If the response is not valid JSON, the API code
                is non-zero, or the ``data`` field is missing.
        """
        url = f"{self.API_BASE}/x/web-interface/view"
        params = {"bvid": bvid}

        try:
            response = self.session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise BilibiliNetworkError(
                f"Failed to fetch video view for {bvid}: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BilibiliApiError(
                f"Invalid JSON response for {bvid}: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise BilibiliApiError(
                f"Unexpected response type for {bvid}: {type(payload).__name__}"
            )

        code = payload.get("code")
        if code != 0:
            message = payload.get("message", "Unknown API error")
            raise BilibiliApiError(
                f"Bilibili API error for {bvid}: code={code}, message={message}"
            )

        data = payload.get("data")
        if data is None:
            raise BilibiliApiError(f"Missing data in response for {bvid}")

        return data

    def fetch_video_meta(
        self,
        input_url: str,
        bvid: str,
        page: int,
        canonical_url: str | None = None,
    ) -> tuple[VideoMeta, list[PageInfo]]:
        """Fetch video view data and build standard models."""
        view_data = self.fetch_video_view(bvid)
        return build_video_meta_from_view(
            input_url, canonical_url, bvid, page, view_data
        )

    def fetch_player_info(
        self, aid: int, cid: int, bvid: str | None = None
    ) -> dict[str, Any]:
        """Fetch player info for a given aid/cid pair.

        Endpoint: GET https://api.bilibili.com/x/player/v2

        This endpoint returns metadata including the list of available subtitle
        tracks. Subtitle content is not downloaded here.

        Raises:
            BilibiliNetworkError: If the HTTP request fails.
            BilibiliApiError: If the response is not valid JSON, the API code
                is non-zero, or the ``data`` field is missing.
        """
        params: dict[str, int | str] = {"aid": aid, "cid": cid}
        if bvid is not None:
            params["bvid"] = bvid

        try:
            response = self.session.get(
                self.PLAYER_V2_URL,
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise BilibiliNetworkError(
                f"Failed to fetch player info for aid={aid}, cid={cid}: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BilibiliApiError(
                f"Invalid JSON player response for aid={aid}, cid={cid}: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise BilibiliApiError(
                f"Unexpected player response type for aid={aid}, cid={cid}: "
                f"{type(payload).__name__}"
            )

        code = payload.get("code")
        if code != 0:
            message = payload.get("message", "Unknown API error")
            raise BilibiliApiError(
                f"Bilibili player API error for aid={aid}, cid={cid}: "
                f"code={code}, message={message}"
            )

        data = payload.get("data")
        if data is None:
            raise BilibiliApiError(
                f"Missing data in player response for aid={aid}, cid={cid}"
            )

        return data

    def fetch_subtitle_tracks_with_status(
        self, aid: int, cid: int, bvid: str | None = None
    ) -> tuple[list[SubtitleTrack], bool]:
        """Fetch subtitle track metadata and login-gating status.

        Returns a tuple of ``(tracks, need_login_subtitle)``. The second value
        is ``True`` when the API indicates that subtitle information requires
        a logged-in session. No subtitle content is downloaded.

        If subtitle tracks are present but all of them lack a ``subtitle_url``,
        the request is retried up to ``self.subtitle_retry_count`` times with
        ``self.subtitle_retry_delay`` seconds between attempts. This mitigates
        transient Bilibili API responses that omit signed subtitle URLs.
        """
        attempts = max(0, self.subtitle_retry_count)
        delay = max(0.0, self.subtitle_retry_delay)

        for attempt in range(attempts + 1):
            player_data = self.fetch_player_info(aid=aid, cid=cid, bvid=bvid)
            tracks = extract_subtitle_tracks(player_data)
            need_login = is_subtitle_login_required(player_data)

            if not tracks:
                return tracks, need_login

            if any(track.subtitle_url for track in tracks):
                return tracks, need_login

            if attempt < attempts:
                time.sleep(delay)

        return tracks, need_login

    def fetch_subtitle_tracks(
        self, aid: int, cid: int, bvid: str | None = None
    ) -> list[SubtitleTrack]:
        """Fetch the list of subtitle tracks for a video page.

        This method only returns subtitle track metadata. It does not download
        the actual subtitle content.
        """
        tracks, _ = self.fetch_subtitle_tracks_with_status(aid, cid, bvid)
        return tracks


def build_video_meta_from_view(
    input_url: str,
    canonical_url: str | None,
    bvid: str,
    page: int,
    view_data: dict[str, Any],
) -> tuple[VideoMeta, list[PageInfo]]:
    """Build ``VideoMeta`` and a list of ``PageInfo`` from view API data.

    Args:
        input_url: The original user input URL.
        canonical_url: Normalized canonical Bilibili URL, if available.
        bvid: The BV id.
        page: Requested page number (1-indexed).
        view_data: The ``data`` object from the view API response.

    Returns:
        A tuple of ``(VideoMeta, list[PageInfo])``. If the requested page does
        not exist, the first page is used instead.
    """
    aid = view_data.get("aid")
    title = view_data.get("title", "")
    owner = view_data.get("owner") or {}
    owner_name = owner.get("name")
    owner_mid = owner.get("mid")
    duration = view_data.get("duration")
    desc = view_data.get("desc")

    raw_pages = view_data.get("pages") or []
    pages: list[PageInfo] = []
    for idx, p in enumerate(raw_pages, start=1):
        pages.append(
            PageInfo(
                page=idx,
                cid=p.get("cid", 0),
                part=p.get("part", ""),
                duration=float(p.get("duration", 0)),
            )
        )

    target_page = page
    if not pages or target_page < 1 or target_page > len(pages):
        target_page = 1

    selected_page = (
        pages[target_page - 1]
        if pages
        else PageInfo(page=1, cid=0, part="", duration=0.0)
    )

    video_meta = VideoMeta(
        platform="bilibili",
        input_url=input_url,
        canonical_url=canonical_url,
        bvid=bvid,
        aid=aid,
        cid=selected_page.cid,
        page=target_page,
        title=title,
        part_title=selected_page.part,
        owner_name=owner_name,
        owner_mid=owner_mid,
        duration=duration,
        desc=desc,
    )

    return video_meta, pages


def _normalize_subtitle_url(url: str | None) -> str | None:
    """Normalize a subtitle URL without making network requests.

    Returns ``None`` for empty URLs, and converts protocol-relative URLs
    (``//...``) to HTTPS.
    """
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _is_ai_subtitle(sub: dict[str, Any]) -> bool:
    """Heuristically determine whether a subtitle track is AI-generated."""
    if sub.get("ai_type") not in (None, 0, ""):
        return True
    if sub.get("type") == "ai":
        return True
    if sub.get("is_ai") is True:
        return True

    for key in ("lan", "id"):
        value = str(sub.get(key, "")).strip().lower()
        if value == "ai" or value.startswith("ai-"):
            return True

    lan_doc = str(sub.get("lan_doc", "")).lower()
    ai_markers = ("自动", "ai", "机器", "生成", "generated", "auto")
    return any(marker in lan_doc for marker in ai_markers)


def extract_subtitle_tracks(player_data: dict[str, Any]) -> list[SubtitleTrack]:
    """Extract subtitle track metadata from player info data.

    Returns an empty list if no subtitle tracks are available. This function
    does not download subtitle content.
    """
    subtitle = player_data.get("subtitle") if isinstance(player_data, dict) else None
    if subtitle is None:
        return []

    raw_tracks = subtitle.get("subtitles")
    if not isinstance(raw_tracks, list):
        return []

    tracks: list[SubtitleTrack] = []
    for sub in raw_tracks:
        if not isinstance(sub, dict):
            continue
        track_id = sub.get("id")
        track_id = str(track_id) if track_id is not None else None
        tracks.append(
            SubtitleTrack(
                id=track_id,
                lan=sub.get("lan", ""),
                lan_doc=sub.get("lan_doc", ""),
                is_ai=_is_ai_subtitle(sub),
                subtitle_url=_normalize_subtitle_url(sub.get("subtitle_url")),
                selected=False,
            )
        )

    return tracks
def is_subtitle_login_required(player_data: dict[str, Any]) -> bool:
    """Return True if the player data indicates subtitles require login.

    This is a pure function that inspects the API response without making
    network requests or reading cookies.
    """
    if not isinstance(player_data, dict):
        return False
    return player_data.get("need_login_subtitle") is True
