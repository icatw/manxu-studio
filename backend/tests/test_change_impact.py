"""Unit tests for IMPACT-CAST / IMPACT-BIBLE field detection."""

from app.schemas.workspace import CharacterPatch, CharacterProfile, ProjectPatch
from app.services.change_impact import bible_impact_fields, cast_visual_changed_fields


def test_cast_visual_detects_appearance_change() -> None:
    before = CharacterProfile(appearance="黑发少年", outfit="校服")
    patch = CharacterPatch(
        profile=CharacterProfile(appearance="银白短发", outfit="校服"),
    )
    assert cast_visual_changed_fields(before, patch) == ["appearance"]


def test_cast_visual_ignores_personality_only() -> None:
    before = CharacterProfile(appearance="黑发少年", personality="沉稳")
    patch = CharacterPatch(
        profile=CharacterProfile(appearance="黑发少年", personality="急躁"),
    )
    assert cast_visual_changed_fields(before, patch) == []


def test_bible_visual_vs_continuity() -> None:
    class Stub:
        world_setting = "旧世界"
        style_rules = "旧规则"
        negative_prompt = ""
        art_style = "日系"
        style_seed = None

    before = Stub()
    reason, fields = bible_impact_fields(
        before, ProjectPatch(style_rules="新规则", world_setting="新世界")
    )
    assert reason == "bible_visual"
    assert fields == ["style_rules", "world_setting"]

    reason2, fields2 = bible_impact_fields(before, ProjectPatch(world_setting="新世界"))
    assert reason2 == "bible_continuity"
    assert fields2 == ["world_setting"]

    reason3, fields3 = bible_impact_fields(before, ProjectPatch(title="仅改标题"))
    assert reason3 is None
    assert fields3 == []
