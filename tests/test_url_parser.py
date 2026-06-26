"""Tests for bili_copilot.url_parser."""

from bili_copilot.url_parser import parse_bili_input


def test_standard_url():
    result = parse_bili_input("https://www.bilibili.com/video/BV1xx411c7mD")
    assert result.input_type == "bilibili_url"
    assert result.bvid == "BV1xx411c7mD"
    assert result.page == 1
    assert result.canonical_url == "https://www.bilibili.com/video/BV1xx411c7mD"
    assert result.needs_short_url_resolution is False


def test_url_with_trailing_slash():
    result = parse_bili_input("https://www.bilibili.com/video/BV1xx411c7mD/")
    assert result.input_type == "bilibili_url"
    assert result.bvid == "BV1xx411c7mD"
    assert result.page == 1


def test_url_with_p2():
    result = parse_bili_input("https://www.bilibili.com/video/BV1xx411c7mD?p=2")
    assert result.input_type == "bilibili_url"
    assert result.bvid == "BV1xx411c7mD"
    assert result.page == 2
    assert result.canonical_url == "https://www.bilibili.com/video/BV1xx411c7mD?p=2"


def test_url_with_extra_params():
    result = parse_bili_input(
        "https://www.bilibili.com/video/BV1xx411c7mD?p=3&spm_id_from=333.999&vd_source=abc"
    )
    assert result.input_type == "bilibili_url"
    assert result.bvid == "BV1xx411c7mD"
    assert result.page == 3
    assert result.canonical_url == "https://www.bilibili.com/video/BV1xx411c7mD?p=3"


def test_no_p_defaults_to_1():
    result = parse_bili_input("https://www.bilibili.com/video/BV1xx411c7mD")
    assert result.page == 1


def test_non_numeric_p_defaults_to_1():
    result = parse_bili_input("https://www.bilibili.com/video/BV1xx411c7mD?p=abc")
    assert result.page == 1


def test_zero_p_defaults_to_1():
    result = parse_bili_input("https://www.bilibili.com/video/BV1xx411c7mD?p=0")
    assert result.page == 1


def test_negative_p_defaults_to_1():
    result = parse_bili_input("https://www.bilibili.com/video/BV1xx411c7mD?p=-1")
    assert result.page == 1


def test_pure_bvid():
    result = parse_bili_input("BV1xx411c7mD")
    assert result.input_type == "bvid"
    assert result.bvid == "BV1xx411c7mD"
    assert result.page == 1
    assert result.canonical_url == "https://www.bilibili.com/video/BV1xx411c7mD"
    assert result.needs_short_url_resolution is False


def test_b23_short_url():
    result = parse_bili_input("https://b23.tv/abc123")
    assert result.input_type == "b23_short_url"
    assert result.bvid is None
    assert result.page == 1
    assert result.canonical_url is None
    assert result.needs_short_url_resolution is True


def test_non_bili_url_is_invalid():
    result = parse_bili_input("https://www.youtube.com/watch?v=123")
    assert result.input_type == "invalid"
    assert result.bvid is None
    assert result.canonical_url is None
    assert result.needs_short_url_resolution is False


def test_empty_string_is_invalid():
    result = parse_bili_input("")
    assert result.input_type == "invalid"
    assert result.bvid is None


def test_whitespace_string_is_invalid():
    result = parse_bili_input("   ")
    assert result.input_type == "invalid"
    assert result.bvid is None


def test_bilibili_without_bvid_is_invalid():
    result = parse_bili_input("https://www.bilibili.com/video/")
    assert result.input_type == "invalid"
    assert result.bvid is None
