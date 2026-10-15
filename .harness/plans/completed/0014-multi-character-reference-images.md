# 0014 Multi-character reference images

## Goal

Story / character draft must generate a cast (not one protagonist) and a reference image for each character, matching scene draft behavior and ASSET-01.

## Root cause

`CHARACTER_DRAFT` + `CharacterGenerationOutput` only ask for one `character`; the handler updates `existing[0]` and generates one image. Season planning can create many characters with text but no refs.

## Plan

1. Schema/prompt: `characters: list` (1–6), prompt asks for full cast.
2. Handler: upsert by index like scenes; per-character lock preserve; sequential ref images; progress distributed (no early 95%).
3. Tests: multi-char create + images; lock preserve; resume checkpoint; update existing tests.
4. Verify: ruff, mypy, targeted pytest.

## Status

- implemented; tests green (`test_workspace_tasks` + `test_character_reference_lock`)
- pending: commit / rebuild worker image for Docker manual verify
## Status

- completed; character draft generates cast + per-character reference images

