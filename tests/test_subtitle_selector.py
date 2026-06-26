"""Tests for bili_copilot.subtitle_selector."""

from bili_copilot.models import SubtitleTrack
from bili_copilot.subtitle_selector import (
    is_chinese_track,
    is_simplified_chinese_track,
    mark_selected_track,
    select_primary_subtitle_track,
)


def _track(
    lan: str,
    lan_doc: str,
    is_ai: bool = False,
    subtitle_url: str | None = None,
) -> SubtitleTrack:
    return SubtitleTrack(
        id=None,
        lan=lan,
        lan_doc=lan_doc,
        is_ai=is_ai,
        subtitle_url=subtitle_url,
        selected=False,
    )


def test_empty_list_returns_none():
    assert select_primary_subtitle_track([]) is None


def test_single_track_returns_it():
    track = _track("en-US", "English")
    assert select_primary_subtitle_track([track]) is track


def test_human_simplified_chinese_beats_ai_simplified_chinese():
    human = _track("zh-CN", "中文（中国）", is_ai=False)
    ai = _track("zh-CN", "中文（中国）", is_ai=True)
    assert select_primary_subtitle_track([ai, human]) is human


def test_ai_simplified_chinese_beats_english():
    ai_zh = _track("zh-CN", "中文（中国）", is_ai=True)
    en = _track("en-US", "English")
    assert select_primary_subtitle_track([en, ai_zh]) is ai_zh


def test_human_traditional_chinese_below_human_simplified_chinese():
    simp = _track("zh-CN", "中文（简体）", is_ai=False)
    trad = _track("zh-TW", "中文（繁体）", is_ai=False)
    assert select_primary_subtitle_track([trad, simp]) is simp


def test_other_chinese_beats_non_chinese():
    trad = _track("zh-TW", "中文（繁体）", is_ai=False)
    en = _track("en-US", "English")
    assert select_primary_subtitle_track([en, trad]) is trad


def test_non_ai_english_beats_ai_english():
    human_en = _track("en-US", "English")
    ai_en = _track("en-US", "English", is_ai=True)
    assert select_primary_subtitle_track([ai_en, human_en]) is human_en


def test_first_non_ai_when_no_chinese():
    en = _track("en-US", "English")
    ja = _track("ja-JP", "日本語", is_ai=True)
    assert select_primary_subtitle_track([ja, en]) is en


def test_first_track_when_all_ai_non_chinese():
    ai_en = _track("en-US", "English", is_ai=True)
    ai_ja = _track("ja-JP", "日本語", is_ai=True)
    assert select_primary_subtitle_track([ai_en, ai_ja]) is ai_en


def test_lan_starting_with_zh_recognized_as_chinese():
    track = _track("zh-mo", "中文")
    assert is_chinese_track(track) is True


def test_lan_doc_auto_with_is_ai_true_still_treated_as_ai():
    track = _track("zh-CN", "中文（自动生成）", is_ai=True)
    assert track.is_ai is True
    assert is_simplified_chinese_track(track) is True


def test_select_does_not_modify_original_selected():
    track = _track("zh-CN", "中文", is_ai=False)
    track.selected = True  # original has selected=True
    original_value = track.selected

    select_primary_subtitle_track([track])

    assert track.selected is original_value


def test_mark_selected_track_returns_new_list_with_one_selected():
    t1 = _track("zh-CN", "中文")
    t2 = _track("en-US", "English")
    original_list = [t1, t2]

    new_list = mark_selected_track(original_list, t1)

    assert new_list is not original_list
    assert new_list[0].selected is True
    assert new_list[1].selected is False
    assert t1.selected is False
    assert t2.selected is False


def test_mark_selected_track_with_none_marks_all_false():
    t1 = _track("zh-CN", "中文")
    t2 = _track("en-US", "English")
    new_list = mark_selected_track([t1, t2], None)

    assert all(not track.selected for track in new_list)


def test_human_zh_cn_beats_ai_zh():
    human = _track("zh-CN", "中文（中国）", is_ai=False)
    ai = _track("ai-zh", "中文", is_ai=True)
    assert select_primary_subtitle_track([ai, human]) is human


def test_ai_zh_beats_english_when_no_human_chinese():
    ai_zh = _track("ai-zh", "中文", is_ai=True)
    en = _track("en-US", "English")
    assert select_primary_subtitle_track([en, ai_zh]) is ai_zh
