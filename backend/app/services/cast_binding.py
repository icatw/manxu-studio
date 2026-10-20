"""Bind storyboard panels to cast members by name (SERIAL cast consistency / F04)."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID


class NamedCastMember(Protocol):
    id: UUID
    name: str


def normalize_cast_name(name: str) -> str:
    compact = "".join(unicodedata.normalize("NFKC", name).split())
    return compact.casefold()


def resolve_panel_character_ids(
    characters: Sequence[NamedCastMember],
    *,
    explicit_names: list[str] | None = None,
    haystack: str = "",
) -> list[str]:
    """Return cast UUIDs mentioned for a panel.

    Prefer LLM-provided ``character_names``, then substring matches against
    dialogue / actions / prompt text. Longest names win first to reduce
    partial overlaps. Returns an empty list when nothing matches (establishing
    shot) instead of defaulting to the first cast member.
    """
    if not characters:
        return []

    by_norm = {
        normalize_cast_name(character.name): character
        for character in characters
        if character.name and character.name.strip()
    }
    ordered = sorted(
        (character for character in characters if character.name and character.name.strip()),
        key=lambda character: len(character.name.strip()),
        reverse=True,
    )

    ids: list[str] = []
    seen: set[str] = set()

    def add(character: NamedCastMember) -> None:
        key = str(character.id)
        if key not in seen:
            seen.add(key)
            ids.append(key)

    for raw in explicit_names or []:
        character = by_norm.get(normalize_cast_name(raw))
        if character is not None:
            add(character)

    text = haystack or ""
    normalized_text = normalize_cast_name(text)
    for character in ordered:
        name = character.name.strip()
        # Skip single Latin letters (noise); allow CJK single-char names like「零」.
        if len(name) < 1 or (len(name) == 1 and name.isascii() and name.isalpha()):
            continue
        if name in text or normalize_cast_name(name) in normalized_text:
            add(character)

    return ids
