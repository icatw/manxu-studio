from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import CharacterRecord, ProjectRecord
from app.tasks.handlers import characters as character_handler
from app.tasks.schemas import CharacterGenerationOutput, GeneratedCharacter


@pytest.mark.asyncio
async def test_character_regen_preserves_locked_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    task_id = uuid4()
    locked_asset_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="雨夜的旧车站",
        synopsis="失忆的修表师在末班车里发现了未来的死亡名单。",
        genre="悬疑",
        art_style="电影感写实",
    )
    existing = CharacterRecord(
        project_id=project_id,
        name="旧名",
        profile={"generation_source": "ai"},
        status="approved",
        version=2,
        reference_asset_id=locked_asset_id,
        reference_locked=True,
    )
    existing.id = uuid4()
    config = SimpleNamespace(
        text_api_key_encrypted=b"text-encrypted",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=b"image-encrypted",
        image_base_url="https://image.example/v1",
        image_model="qwen-image-test",
    )
    image_calls: list[object] = []

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            assert model is ProjectRecord
            return project

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [existing])

        def add(self, item: object) -> None:
            raise AssertionError("should reuse existing character")

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def configured_model(session: object, account_id: object) -> SimpleNamespace:
        return config

    async def generate_text(**kwargs: object) -> CharacterGenerationOutput:
        return CharacterGenerationOutput(
            character=GeneratedCharacter(
                name="沈知遥",
                role="表行学徒",
                appearance="二十六岁，清瘦。",
                hairstyle="齐耳黑发",
                outfit="旧深绿工装外套",
                signature_traits=["停摆的怀表"],
                personality="克制多疑",
                reference_image_prompt="全身角色立绘",
            )
        )

    async def generate_image(**kwargs: object) -> str:
        image_calls.append(kwargs)
        return "/api/v1/assets/should-not-run.png"

    async def noop_clear(*args: object, **kwargs: object) -> None:
        return None

    async def noop_persist(*args: object, **kwargs: object) -> None:
        return None

    async def noop_progress(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda encrypted: "key")
    monkeypatch.setattr(character_handler, "generate_structured_text", generate_text)
    monkeypatch.setattr(character_handler, "generate_image", generate_image)
    monkeypatch.setattr(character_handler, "text_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr(character_handler, "clear_image_job", noop_clear)
    monkeypatch.setattr(character_handler, "persist_text_checkpoint", noop_persist)
    monkeypatch.setattr(character_handler, "report_progress", noop_progress)

    task = SimpleNamespace(id=task_id, project_id=project_id, progress=5, provider_state={})
    result = await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    assert image_calls == []
    assert existing.reference_asset_id == locked_asset_id
    assert existing.reference_locked is True
    assert existing.name == "沈知遥"
    assert result["reference_locked_preserved"] is True
    assert result["reference_image_generated"] is True
