"""ASSET-01: locked cast visual anchors must reach panel image prompts."""

from types import SimpleNamespace

from app.tasks.handlers.characters import build_locked_character_consistency_constraint
from app.tasks.handlers.panel_image import build_panel_image_prompt
from app.tasks.prompts import (
    STORYBOARD_DRAFT,
    STORYBOARD_IMAGE_PROMPT_CAST_RULE,
)


def test_locked_constraint_includes_hairstyle_outfit_and_anti_blonde() -> None:
    text = build_locked_character_consistency_constraint(
        name="苏青",
        profile={
            "appearance": "红唇，精致妆容，皮肤冷白",
            "hairstyle": "干练的深栗色侧马尾，禁止金发",
            "outfit": "红色西装外套，白色丝绸衬衫",
            "signature_traits": ["佩戴珍珠耳钉", "手持拿铁"],
            "image_prompt": "气场强大",
        },
        has_reference_asset=True,
    )
    assert "发型必须为：干练的深栗色侧马尾" in text
    assert "服装必须为：红色西装外套" in text
    assert "珍珠耳钉" in text
    assert "禁止擅自改为金发" in text
    assert "定妆参考图" in text


def test_non_corporeal_skips_hair_anti_drift() -> None:
    text = build_locked_character_consistency_constraint(
        name="Eve",
        profile={
            "appearance": "无实体，蓝色数据流",
            "hairstyle": "无",
            "outfit": "无",
        },
    )
    assert "发型必须为" not in text
    assert "禁止擅自改为金发" not in text


def test_panel_prompt_includes_image_prompt_and_cast_lock() -> None:
    panel = SimpleNamespace(
        scene_description="天台雨夜",
        shot="中景",
        composition="二人对立",
        character_actions="苏青递咖啡",
        emotion="对峙",
        image_prompt="苏青，深栗色侧马尾，红色西装，珍珠耳钉，拿铁",
    )
    cast = build_locked_character_consistency_constraint(
        name="苏青",
        profile={
            "appearance": "冷白皮肤",
            "hairstyle": "深栗色侧马尾",
            "outfit": "红色西装",
        },
    )
    prompt = build_panel_image_prompt(
        art_style="日系赛博漫画",
        style_rules="冷色调",
        negative_prompt="blonde hair, yellow hair",
        panel=panel,  # type: ignore[arg-type]
        locked_character_constraints=[cast],
        instruction="保持定妆",
    )
    assert "深栗色侧马尾，红色西装，珍珠耳钉" in prompt
    assert "发型必须为：深栗色侧马尾" in prompt
    assert "blonde hair, yellow hair" in prompt
    assert "无文字、无水印" in prompt


def test_storyboard_prompt_requires_cast_visual_anchors_in_image_prompt() -> None:
    assert "栗色侧马尾" in STORYBOARD_IMAGE_PROMPT_CAST_RULE
    assert STORYBOARD_IMAGE_PROMPT_CAST_RULE in STORYBOARD_DRAFT.system
    assert "neat side ponytail" in STORYBOARD_IMAGE_PROMPT_CAST_RULE
