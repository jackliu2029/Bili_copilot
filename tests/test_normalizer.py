"""Tests for bili_copilot.normalizer."""

from bili_copilot.models import TranscriptSegment
from bili_copilot.normalizer import normalize_subtitle_body, normalize_subtitle_json


def test_normalize_standard_body():
    payload = {
        "body": [
            {"from": 1.2, "to": 3.4, "content": "字幕文本"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert len(segments) == 1
    assert segments[0] == TranscriptSegment(start=1.2, end=3.4, text="字幕文本")


def test_normalize_preserves_order():
    payload = {
        "body": [
            {"from": 0.0, "to": 2.0, "content": "第一句"},
            {"from": 2.0, "to": 4.0, "content": "第二句"},
            {"from": 4.0, "to": 6.0, "content": "第三句"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert [seg.text for seg in segments] == ["第一句", "第二句", "第三句"]


def test_normalize_missing_body_returns_empty():
    assert normalize_subtitle_json({}) == []


def test_normalize_body_none_returns_empty():
    assert normalize_subtitle_json({"body": None}) == []


def test_normalize_body_not_list_returns_empty():
    assert normalize_subtitle_json({"body": "not a list"}) == []


def test_normalize_skips_missing_from():
    payload = {
        "body": [
            {"to": 2.0, "content": "第一句"},
            {"from": 2.0, "to": 4.0, "content": "第二句"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert len(segments) == 1
    assert segments[0].text == "第二句"


def test_normalize_skips_missing_to():
    payload = {
        "body": [
            {"from": 0.0, "content": "第一句"},
            {"from": 2.0, "to": 4.0, "content": "第二句"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert len(segments) == 1
    assert segments[0].text == "第二句"


def test_normalize_skips_missing_content():
    payload = {
        "body": [
            {"from": 0.0, "to": 2.0},
            {"from": 2.0, "to": 4.0, "content": "第二句"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert len(segments) == 1
    assert segments[0].text == "第二句"


def test_normalize_skips_invalid_time():
    payload = {
        "body": [
            {"from": "abc", "to": 2.0, "content": "第一句"},
            {"from": 2.0, "to": "def", "content": "第二句"},
            {"from": 4.0, "to": 6.0, "content": "第三句"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert len(segments) == 1
    assert segments[0].text == "第三句"


def test_normalize_strips_text_whitespace():
    payload = {
        "body": [
            {"from": 0.0, "to": 2.0, "content": "  字幕  "},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert segments[0].text == "字幕"


def test_normalize_does_not_merge_segments():
    payload = {
        "body": [
            {"from": 0.0, "to": 2.0, "content": "第一句"},
            {"from": 2.0, "to": 4.0, "content": "第二句"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert len(segments) == 2


def test_normalize_preserves_chinese_text():
    payload = {
        "body": [
            {"from": 0.0, "to": 2.0, "content": "你好，世界！"},
        ]
    }
    segments = normalize_subtitle_json(payload)

    assert segments[0].text == "你好，世界！"


def test_normalize_body_directly():
    body = [
        {"from": 1, "to": 3, "content": "直接传入 body"},
    ]
    segments = normalize_subtitle_body(body)

    assert len(segments) == 1
    assert segments[0].text == "直接传入 body"
