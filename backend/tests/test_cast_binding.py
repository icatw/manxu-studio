from types import SimpleNamespace
from uuid import uuid4

from app.services.cast_binding import resolve_panel_character_ids


def test_resolve_prefers_explicit_names_and_avoids_first_cast_default() -> None:
    lin = SimpleNamespace(id=uuid4(), name="林澈")
    gu = SimpleNamespace(id=uuid4(), name="顾承川")
    zero = SimpleNamespace(id=uuid4(), name="零")

    ids = resolve_panel_character_ids(
        [gu, lin, zero],
        explicit_names=["林澈", "零"],
        haystack="顾承川在远景路过",
    )
    assert ids == [str(lin.id), str(zero.id), str(gu.id)]


def test_resolve_matches_dialogue_substring_longest_first() -> None:
    short = SimpleNamespace(id=uuid4(), name="林")
    long = SimpleNamespace(id=uuid4(), name="林澈")
    ids = resolve_panel_character_ids(
        [short, long],
        haystack="林澈：今晚别出门。",
    )
    assert str(long.id) in ids
    assert ids[0] == str(long.id)


def test_resolve_empty_when_no_match() -> None:
    only = SimpleNamespace(id=uuid4(), name="顾承川")
    assert resolve_panel_character_ids([only], haystack="空镜：港口夜色") == []
