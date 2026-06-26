"""Tests for the local Cookie file reader and redaction utilities."""

import os
from pathlib import Path

import pytest

from bili_copilot.cookie_config import (
    CookieConfigError,
    CookieFileEmptyError,
    CookieFileNotFoundError,
    CookieParseError,
    build_cookie_header,
    get_cookie_file_from_env,
    load_cookie_header_from_file,
    parse_cookie_text,
    redact_cookie_header,
    redact_cookie_value,
)

_FAKE_SESSDATA = "fake_session_value_12345"
_FAKE_BILI_JCT = "fake_csrf_value_67890"
_FAKE_DEDEUSERID = "fake_user_id_42"


class TestParseCookieText:
    def test_parses_key_value_lines(self) -> None:
        text = (
            f"SESSDATA={_FAKE_SESSDATA}\n"
            f"bili_jct={_FAKE_BILI_JCT}\n"
            f"DedeUserID={_FAKE_DEDEUSERID}\n"
        )
        cookies = parse_cookie_text(text)
        assert cookies == {
            "SESSDATA": _FAKE_SESSDATA,
            "bili_jct": _FAKE_BILI_JCT,
            "DedeUserID": _FAKE_DEDEUSERID,
        }

    def test_ignores_empty_lines(self) -> None:
        text = f"\n\nSESSDATA={_FAKE_SESSDATA}\n\n"
        cookies = parse_cookie_text(text)
        assert cookies == {"SESSDATA": _FAKE_SESSDATA}

    def test_ignores_comment_lines(self) -> None:
        text = (
            "# This is a comment\n"
            f"SESSDATA={_FAKE_SESSDATA}\n"
            "# another comment\n"
        )
        cookies = parse_cookie_text(text)
        assert cookies == {"SESSDATA": _FAKE_SESSDATA}

    def test_strips_keys_and_values(self) -> None:
        text = f"  SESSDATA  =  {_FAKE_SESSDATA}  \n"
        cookies = parse_cookie_text(text)
        assert cookies == {"SESSDATA": _FAKE_SESSDATA}

    def test_rejects_empty_key(self) -> None:
        with pytest.raises(CookieParseError) as exc_info:
            parse_cookie_text(f"={_FAKE_SESSDATA}")
        assert _FAKE_SESSDATA not in str(exc_info.value)

    def test_rejects_empty_value(self) -> None:
        with pytest.raises(CookieParseError) as exc_info:
            parse_cookie_text("SESSDATA=")
        assert "SESSDATA=" not in str(exc_info.value)
        assert _FAKE_SESSDATA not in str(exc_info.value)

    def test_rejects_malformed_line(self) -> None:
        with pytest.raises(CookieParseError) as exc_info:
            parse_cookie_text(f"no_equals_here_{_FAKE_SESSDATA}")
        assert _FAKE_SESSDATA not in str(exc_info.value)

    def test_rejects_empty_text(self) -> None:
        with pytest.raises(CookieFileEmptyError):
            parse_cookie_text("")

    def test_rejects_whitespace_only_text(self) -> None:
        with pytest.raises(CookieFileEmptyError):
            parse_cookie_text("   \n\n  ")

    def test_rejects_comment_only_text(self) -> None:
        with pytest.raises(CookieFileEmptyError):
            parse_cookie_text("# only comments\n# more comments")

    def test_rejects_non_string_input(self) -> None:
        with pytest.raises(CookieParseError):
            parse_cookie_text(None)  # type: ignore[arg-type]


class TestBuildCookieHeader:
    def test_builds_header_with_sorted_keys(self) -> None:
        cookies = {
            "bili_jct": _FAKE_BILI_JCT,
            "SESSDATA": _FAKE_SESSDATA,
        }
        header = build_cookie_header(cookies)
        assert header == f"SESSDATA={_FAKE_SESSDATA}; bili_jct={_FAKE_BILI_JCT}"

    def test_rejects_empty_mapping(self) -> None:
        with pytest.raises(CookieFileEmptyError):
            build_cookie_header({})

    def test_header_contains_all_keys(self) -> None:
        cookies = {
            "SESSDATA": _FAKE_SESSDATA,
            "bili_jct": _FAKE_BILI_JCT,
            "DedeUserID": _FAKE_DEDEUSERID,
        }
        header = build_cookie_header(cookies)
        assert "SESSDATA=" in header
        assert "bili_jct=" in header
        assert "DedeUserID=" in header


class TestLoadCookieHeaderFromFile:
    def test_loads_valid_cookie_file(self, tmp_path: Path) -> None:
        cookie_file = tmp_path / "bili_cookie.txt"
        cookie_file.write_text(
            f"SESSDATA={_FAKE_SESSDATA}\nbili_jct={_FAKE_BILI_JCT}\n", encoding="utf-8"
        )
        header = load_cookie_header_from_file(cookie_file)
        assert _FAKE_SESSDATA in header
        assert _FAKE_BILI_JCT in header

    def test_loads_file_with_comments_and_blank_lines(self, tmp_path: Path) -> None:
        cookie_file = tmp_path / "bili_cookie.txt"
        cookie_file.write_text(
            "# login cookie\n\n"
            f"SESSDATA={_FAKE_SESSDATA}\n\n"
            f"# csrf\nbili_jct={_FAKE_BILI_JCT}\n",
            encoding="utf-8",
        )
        header = load_cookie_header_from_file(cookie_file)
        assert _FAKE_SESSDATA in header
        assert _FAKE_BILI_JCT in header

    def test_raises_when_file_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.txt"
        with pytest.raises(CookieFileNotFoundError):
            load_cookie_header_from_file(missing)

    def test_raises_when_path_is_directory(self, tmp_path: Path) -> None:
        with pytest.raises(CookieFileNotFoundError):
            load_cookie_header_from_file(tmp_path)

    def test_raises_when_file_empty(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        with pytest.raises(CookieFileEmptyError):
            load_cookie_header_from_file(empty_file)

    def test_raises_when_file_only_comments(self, tmp_path: Path) -> None:
        comment_file = tmp_path / "comments.txt"
        comment_file.write_text("# comment\n", encoding="utf-8")
        with pytest.raises(CookieFileEmptyError):
            load_cookie_header_from_file(comment_file)

    def test_raises_parse_error_and_does_not_leak_value(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.txt"
        bad_file.write_text(
            f"SESSDATA={_FAKE_SESSDATA}\nmalformed_line_no_equals\n", encoding="utf-8"
        )
        with pytest.raises(CookieParseError) as exc_info:
            load_cookie_header_from_file(bad_file)
        assert _FAKE_SESSDATA not in str(exc_info.value)


class TestGetCookieFileFromEnv:
    def test_returns_path_when_env_set(self) -> None:
        env = {"BILI_COOKIE_FILE": "/path/to/cookie.txt"}
        result = get_cookie_file_from_env(env)
        assert result == Path("/path/to/cookie.txt")

    def test_returns_none_when_env_missing(self) -> None:
        env = {}
        assert get_cookie_file_from_env(env) is None

    def test_returns_none_when_env_empty(self) -> None:
        env = {"BILI_COOKIE_FILE": "   "}
        assert get_cookie_file_from_env(env) is None

    def test_uses_os_environ_by_default(self, monkeypatch) -> None:
        monkeypatch.setenv("BILI_COOKIE_FILE", "/default/cookie.txt")
        result = get_cookie_file_from_env()
        assert result == Path("/default/cookie.txt")


class TestRedactCookieValue:
    def test_redacts_short_value(self) -> None:
        assert redact_cookie_value("abc") == "<redacted>"

    def test_redacts_long_value_with_prefix_suffix(self) -> None:
        value = "abcdefghij"
        redacted = redact_cookie_value(value)
        assert redacted == "abcd...ghij"
        assert value not in redacted or len(value) <= 8

    def test_redacts_fake_session_value(self) -> None:
        redacted = redact_cookie_value(_FAKE_SESSDATA)
        assert _FAKE_SESSDATA not in redacted


class TestRedactCookieHeader:
    def test_redacts_all_values(self) -> None:
        header = f"SESSDATA={_FAKE_SESSDATA}; bili_jct={_FAKE_BILI_JCT}"
        redacted = redact_cookie_header(header)
        assert "SESSDATA=<redacted>" in redacted
        assert "bili_jct=<redacted>" in redacted
        assert _FAKE_SESSDATA not in redacted
        assert _FAKE_BILI_JCT not in redacted

    def test_handles_empty_header(self) -> None:
        assert redact_cookie_header("") == ""

    def test_handles_whitespace_header(self) -> None:
        assert redact_cookie_header("   ") == ""

    def test_handles_single_pair(self) -> None:
        redacted = redact_cookie_header(f"SESSDATA={_FAKE_SESSDATA}")
        assert redacted == "SESSDATA=<redacted>"


class TestExceptionMessagesDoNotLeakCookies:
    def test_file_not_found_message_no_cookie(self, tmp_path: Path) -> None:
        path = tmp_path / "secret_cookie.txt"
        with pytest.raises(CookieFileNotFoundError) as exc_info:
            load_cookie_header_from_file(path)
        assert _FAKE_SESSDATA not in str(exc_info.value)

    def test_parse_error_message_no_cookie(self) -> None:
        with pytest.raises(CookieParseError) as exc_info:
            parse_cookie_text(f"no_value {_FAKE_SESSDATA}")
        assert _FAKE_SESSDATA not in str(exc_info.value)


def test_cookie_config_error_inheritance() -> None:
    assert issubclass(CookieFileNotFoundError, CookieConfigError)
    assert issubclass(CookieFileEmptyError, CookieConfigError)
    assert issubclass(CookieParseError, CookieConfigError)
