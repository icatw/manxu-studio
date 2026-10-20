"""Unit tests for vertical-strip seed bubble geometry (0036 / 0040)."""

from app.services.lettering import (
    default_seed_bubble_geometry,
    leading_speaker_name,
    seed_bubble_tail,
    width_pct_for_text,
)


def test_single_short_line_top_center_band() -> None:
    geo = default_seed_bubble_geometry(bubble_index=0, text="你好。", bubble_count=1)
    assert geo.x_pct == 20.0
    assert geo.y_pct == 5.0
    assert geo.font_size == "lg"
    assert geo.width_pct == 48.0
    assert geo.tail == "none"


def test_multi_bubble_uses_dialogue_lr_geometry() -> None:
    first = default_seed_bubble_geometry(bubble_index=0, text="先说。", bubble_count=2)
    second = default_seed_bubble_geometry(bubble_index=1, text="后说。", bubble_count=2)
    assert first.x_pct == 8.0
    assert second.x_pct == 48.0
    assert first.y_pct < second.y_pct
    assert first.tail == "bottom_left"
    assert second.tail == "bottom_right"


def test_width_grows_with_text_length() -> None:
    short = default_seed_bubble_geometry(bubble_index=0, text="短")
    medium = default_seed_bubble_geometry(
        bubble_index=0,
        text="这是一句明显更长的对白，用来拉宽气泡宽度。",
    )
    long = default_seed_bubble_geometry(
        bubble_index=0,
        text="这是一句明显更长的对白，用来拉宽气泡宽度并触发小号字号。" * 3,
    )
    assert short.width_pct < medium.width_pct <= long.width_pct
    assert long.width_pct == 84.0
    assert long.font_size == "sm"
    assert width_pct_for_text("短") == 48.0


def test_geometry_ignores_panel_slot_parity() -> None:
    """Same text at bubble_index 0 must not depend on which panel/slot it came from."""
    a = default_seed_bubble_geometry(bubble_index=0, text="同一句对白内容。")
    b = default_seed_bubble_geometry(bubble_index=0, text="同一句对白内容。")
    assert a == b
    assert a.x_pct == 20.0
    assert a.tail == "none"


def test_unmatched_speaker_tail_none() -> None:
    assert seed_bubble_tail("路人：你好。", ["林深", "苏青"]) == "none"
    assert leading_speaker_name("没有冒号的一句") is None
    geo = default_seed_bubble_geometry(
        bubble_index=0,
        text="你好。",
        cast_names=["林深", "苏青"],
        speaker_source="路人：你好。",
        bubble_count=1,
    )
    assert geo.tail == "none"


def test_matched_cast_tails_left_then_right() -> None:
    cast = ["林深", "苏青"]
    assert seed_bubble_tail("林深：这是我的解法。", cast) == "bottom_left"
    assert seed_bubble_tail("苏青：有趣。", cast) == "bottom_right"
    first = default_seed_bubble_geometry(
        bubble_index=0,
        text="这是我的解法。",
        cast_names=cast,
        speaker_source="林深：这是我的解法。",
        bubble_count=2,
    )
    second = default_seed_bubble_geometry(
        bubble_index=1,
        text="有趣。",
        cast_names=cast,
        speaker_source="苏青：有趣。",
        bubble_count=2,
    )
    assert first.tail == "bottom_left"
    assert second.tail == "bottom_right"
    assert first.x_pct < second.x_pct
