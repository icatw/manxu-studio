"""Unit tests for character reference image prompt assembly."""

from app.tasks.handlers.characters import build_character_reference_image_prompt


def test_corporeal_prompt_binds_hairstyle_outfit_and_face_framing() -> None:
    prompt = build_character_reference_image_prompt(
        art_style="都市漫画",
        name="林深",
        profile={
            "role": "男主角",
            "appearance": "苍白皮肤，黑眼圈",
            "hairstyle": "凌乱黑发",
            "outfit": "黑色高领毛衣，深色工装裤",
            "signature_traits": ["手指修长且布满旧伤"],
            "image_prompt": "氛围压抑",
        },
    )
    assert "发型必须为：凌乱黑发" in prompt
    assert "服装必须为：黑色高领毛衣，深色工装裤" in prompt
    assert "禁止切头" in prompt
    assert "脸部五官清晰可见" in prompt
    assert "补充氛围：氛围压抑" in prompt


def test_non_corporeal_prompt_avoids_full_body_human() -> None:
    prompt = build_character_reference_image_prompt(
        art_style="赛博漫画",
        name="ChatGPT",
        profile={
            "role": "AI助手",
            "appearance": "无实体，视觉化为幽蓝色数据流",
            "hairstyle": "无",
            "outfit": "无",
            "signature_traits": ["合成感语音"],
            "image_prompt": "错误地写成了和服少女",
        },
    )
    assert "非实体角色抽象可视化" in prompt
    assert "不要画成完整真人全身像" in prompt
    assert "发型必须为" not in prompt
    assert "单人全身角色设定立绘" not in prompt
