import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.db.models import (
    AccountModelConfigRecord,
    CharacterRecord,
    EpisodeRecord,
    ProjectRecord,
    SceneRecord,
)
from app.providers.errors import RecoverableProviderError
from app.schemas.workspace import SceneProfile
from app.tasks.handlers import characters as character_handler
from app.tasks.handlers import scenes as scene_handler
from app.tasks.handlers import storyboard as storyboard_handler
from app.tasks.schemas import (
    CharacterGenerationOutput,
    GeneratedCharacter,
    GeneratedPanel,
    GeneratedScene,
    SceneGenerationOutput,
    StoryboardGenerationOutput,
)


@pytest.mark.asyncio
async def test_storyboard_replacement_flushes_deletes_before_inserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    episode_id = uuid4()
    project_id = uuid4()
    existing_panel = object()
    episode = SimpleNamespace(synopsis="A story", position=0)
    project = SimpleNamespace(
        owner_id=uuid4(),
        title="Title",
        genre="幻想",
        art_style="漫画",
        world_setting="",
    )
    results = iter([[], [], [existing_panel]])

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            if model is EpisodeRecord:
                assert record_id == episode_id
                return episode
            if model is ProjectRecord:
                assert record_id == project_id
                return project
            raise AssertionError(f"Unexpected model: {model}")

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: next(results))

        async def delete(self, item: object) -> None:
            assert item is existing_panel
            events.append("delete")

        def add(self, item: object) -> None:
            events.append("add")

        async def flush(self) -> None:
            events.append("flush")

        async def commit(self) -> None:
            events.append("commit")

    async def configured_model(session: object, owner_id: object) -> SimpleNamespace:
        assert owner_id == project.owner_id
        return SimpleNamespace(
            text_api_key_encrypted=b"encrypted",
            text_base_url="https://example.com/v1",
            text_model="test",
        )

    async def generate_text(**kwargs: object) -> StoryboardGenerationOutput:
        assert kwargs["response_model"] is StoryboardGenerationOutput
        return StoryboardGenerationOutput(
            panels=[
                GeneratedPanel(
                    shot="中景",
                    scene_description="A scene",
                    composition="Centered",
                    character_actions="Walks in",
                    emotion="Calm",
                    story_purpose="Introduce character",
                    image_prompt="Comic panel",
                )
            ]
        )

    async def empty_continuity(
        session: object, project_id_arg: object, *, before_position: int | None = None
    ) -> SimpleNamespace:
        _ = before_position
        return SimpleNamespace(world_setting="", previous_summaries=[], open_threads=[])

    monkeypatch.setattr(storyboard_handler, "require_text_model", configured_model)
    monkeypatch.setattr(storyboard_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(storyboard_handler, "generate_structured_text", generate_text)
    monkeypatch.setattr("app.services.serial_service.build_continuity", empty_continuity)

    task = SimpleNamespace(
        request_data={"episode_id": str(episode_id), "panel_count": 1, "use_continuity": True},
        project_id=project_id,
    )

    result = await storyboard_handler.generate_panels(FakeSession(), task)  # type: ignore[arg-type]

    assert events == ["commit", "commit", "commit", "delete", "flush", "add", "flush"]
    assert result["episode_id"] == str(episode_id)


@pytest.mark.asyncio
async def test_character_generation_calls_text_and_image_models_and_marks_ai_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    task_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="雨夜的旧车站",
        synopsis="失忆的修表师在末班车里发现了未来的死亡名单。",
        genre="悬疑",
        art_style="电影感写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text-encrypted",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=b"image-encrypted",
        image_base_url="https://image.example/v1",
        image_model="qwen-image-test",
    )
    created: list[CharacterRecord] = []
    progress: list[int] = []
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            assert model is ProjectRecord
            assert record_id == project_id
            return project

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [])

        def add(self, item: CharacterRecord) -> None:
            item.id = uuid4()
            created.append(item)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            progress.append(task.progress)

    async def configured_model(session: object, account_id: object) -> SimpleNamespace:
        assert account_id == owner_id
        return config

    async def generate_text(**kwargs: object) -> CharacterGenerationOutput:
        calls.append(("text", kwargs))
        assert kwargs["base_url"] == config.text_base_url
        assert kwargs["model"] == config.text_model
        assert kwargs["api_key"] == "decrypted-text-key"
        return CharacterGenerationOutput(
            characters=[
                GeneratedCharacter(
                    name="沈知遥",
                    role="表行学徒，能通过修表回放物件最后一次滴答",
                    appearance="二十六岁，清瘦，左眉有一道被玻璃划出的浅疤。",
                    hairstyle="齐耳黑发，雨水打湿后贴在脸侧。",
                    outfit="旧深绿工装外套，袖口缝着银线。",
                    signature_traits=["停摆的怀表", "左眉浅疤"],
                    personality="克制多疑，遇到失踪儿童线索时会冒险追查。",
                    reference_image_prompt="全身角色立绘，深绿工装外套，银线袖口，左眉浅疤。",
                ),
                GeneratedCharacter(
                    name="苏晚",
                    role="女主，调查记者",
                    appearance="明亮大眼，气质干练。",
                    hairstyle="侧扎长发",
                    outfit="米色风衣、衬衫、及膝裙",
                    signature_traits=["随身录音笔"],
                    personality="敏锐、正直",
                    reference_image_prompt="全身角色立绘，米色风衣，侧扎长发。",
                ),
            ]
        )

    async def generate_image(**kwargs: object) -> str:
        calls.append(("image", kwargs))
        assert kwargs["model"] == config.image_model
        assert kwargs["base_url"] == config.image_base_url
        assert kwargs["prompt_extend"] is False
        return "/api/v1/assets/generated.png"

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(
        character_handler,
        "decrypt_secret",
        lambda encrypted: (
            "decrypted-text-key" if encrypted == b"text-encrypted" else "decrypted-image-key"
        ),
    )
    monkeypatch.setattr(character_handler, "generate_structured_text", generate_text)
    monkeypatch.setattr(character_handler, "generate_image", generate_image)

    task = SimpleNamespace(id=task_id, project_id=project_id, progress=5, request_data={})
    result = await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    assert [name for name, _ in calls][0] == "text"
    assert [name for name, _ in calls].count("image") == 2
    assert len(created) == 2
    assert created[0].name == "沈知遥"
    assert created[1].name == "苏晚"
    assert created[0].profile["generation_source"] == "ai"
    image_calls = [dict(payload) for name, payload in calls if name == "image"]
    by_name = {
        "沈知遥": next(item for item in image_calls if "沈知遥" in str(item["prompt"])),
        "苏晚": next(item for item in image_calls if "苏晚" in str(item["prompt"])),
    }
    assert created[0].reference_asset_id == by_name["沈知遥"]["asset_id"]
    assert created[1].reference_asset_id == by_name["苏晚"]["asset_id"]
    assert result["generation_source"] == "ai"
    assert result["reference_image_generated"] is True
    assert result["reference_images_generated"] == 2
    assert progress == sorted(progress)
    assert progress[-1] == 95
    assert task.request_data["text_checkpoints"]["characters"]["done"] is True
    assert task.request_data["text_checkpoints"]["characters"]["character_ids"] == [
        str(created[0].id),
        str(created[1].id),
    ]


@pytest.mark.asyncio
async def test_character_resume_skips_text_and_does_not_reuse_stale_image_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    character_id = uuid4()
    character = CharacterRecord(project_id=project_id, status="draft")
    character.id = character_id
    character.name = "沈知遥"
    character.profile = {
        "generation_source": "ai",
        "image_prompt": "全身角色立绘，深绿工装外套。",
    }
    character.reference_asset_id = None
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="雨夜的旧车站",
        synopsis="梗概",
        genre="悬疑",
        art_style="电影感写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text-encrypted",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=b"image-encrypted",
        image_base_url="https://image.example/v1",
        image_model="qwen-image-test",
    )
    calls: list[str] = []

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            if model is ProjectRecord:
                return project
            if model is CharacterRecord:
                assert record_id == character_id
                return character
            raise AssertionError(f"Unexpected model: {model}")

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [character])

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def configured_model(session: object, account_id: object) -> SimpleNamespace:
        return config

    async def unexpected_text(**kwargs: object) -> None:
        raise AssertionError("text checkpoint must skip LLM")

    async def generate_image(**kwargs: object) -> str:
        calls.append("image")
        assert kwargs.get("resume_task_id") is None
        assert kwargs.get("prompt_extend") is False
        return f"/api/v1/assets/{kwargs['asset_id']}"

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(character_handler, "generate_structured_text", unexpected_text)
    monkeypatch.setattr(character_handler, "generate_image", generate_image)

    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        progress=5,
        request_data={
            "text_checkpoints": {
                "characters": {"done": True, "character_ids": [str(character_id)]}
            },
            # Stale remote job from a previous profile must not be resumed after text regen.
            # Text checkpoint path never clears it again; clearing happens on text write.
            # Simulate post-clear empty provider_jobs (correct resume after text snapshot).
            "provider_jobs": {},
        },
    )
    result = await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    assert calls == ["image"]
    assert result["character_ids"] == [str(character_id)]
    assert character.reference_asset_id is not None


@pytest.mark.asyncio
async def test_full_character_regen_deletes_orphan_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    keeper = CharacterRecord(project_id=project_id, status="draft", name="旧一")
    keeper.id = uuid4()
    keeper.version = 1
    keeper.profile = {"generation_source": "ai", "image_prompt": "旧"}
    orphan = CharacterRecord(project_id=project_id, status="approved", name="陆沉")
    orphan.id = uuid4()
    orphan.version = 1
    orphan.profile = {"generation_source": "ai", "image_prompt": "旧"}
    existing = [keeper, orphan]
    deleted: list[UUID] = []
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="重生",
        synopsis="梗概",
        genre="都市",
        art_style="写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=None,
        image_model="qwen-image-test",
        image_base_url="https://image.example/v1",
    )
    panel = SimpleNamespace(character_ids=[str(keeper.id), str(orphan.id)], scene_id=None)
    scalar_calls = {"n": 0}

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            assert model is ProjectRecord
            return project

        async def scalars(self, query: object) -> SimpleNamespace:
            scalar_calls["n"] += 1
            if scalar_calls["n"] == 1:
                return SimpleNamespace(all=lambda: existing)
            if scalar_calls["n"] == 2:
                return SimpleNamespace(all=lambda: [uuid4()])
            return SimpleNamespace(all=lambda: [panel])

        async def delete(self, item: CharacterRecord) -> None:
            deleted.append(item.id)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def generate_text(**kwargs: object) -> CharacterGenerationOutput:
        return CharacterGenerationOutput(
            characters=[
                GeneratedCharacter(
                    name="新主角",
                    role="主角",
                    appearance="外貌",
                    hairstyle="发型",
                    outfit="服装",
                    signature_traits=["特征"],
                    personality="性格",
                    reference_image_prompt="立绘",
                )
            ]
        )

    async def configured_model(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return config

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(character_handler, "generate_structured_text", generate_text)

    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        progress=5,
        request_data={"cast_mode": "replace"},
    )
    result = await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    assert deleted == [orphan.id]
    assert result["character_ids"] == [str(keeper.id)]
    assert panel.character_ids == [str(keeper.id)]
    assert keeper.name == "新主角"


@pytest.mark.asyncio
async def test_append_character_cast_keeps_orphans_and_skips_same_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    existing = CharacterRecord(project_id=project_id, status="approved", name="陆沉")
    existing.id = uuid4()
    existing.version = 2
    existing.profile = {
        "generation_source": "ai",
        "role": "男主",
        "image_prompt": "旧定妆",
    }
    existing.reference_locked = True
    existing.reference_asset_id = uuid4()
    created: list[CharacterRecord] = []
    deleted: list[UUID] = []
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="重生",
        synopsis="梗概",
        genre="都市",
        art_style="写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=None,
        image_model="qwen-image-test",
        image_base_url="https://image.example/v1",
    )

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            assert model is ProjectRecord
            return project

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [existing])

        def add(self, item: CharacterRecord) -> None:
            if not getattr(item, "id", None):
                item.id = uuid4()
            created.append(item)

        async def delete(self, item: CharacterRecord) -> None:
            deleted.append(item.id)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def generate_text(**kwargs: object) -> CharacterGenerationOutput:
        user_prompt = str(kwargs.get("user_prompt", ""))
        assert "陆沉" in user_prompt
        assert "请勿返回" in user_prompt or "仅在剧情确实需要时补充新人" in user_prompt
        return CharacterGenerationOutput(
            characters=[
                GeneratedCharacter(
                    name=" 陆 沉 ",
                    role="男主改写",
                    appearance="应被跳过",
                    hairstyle="发型",
                    outfit="服装",
                    signature_traits=["特征"],
                    personality="性格",
                    reference_image_prompt="立绘",
                ),
                GeneratedCharacter(
                    name="新人",
                    role="配角",
                    appearance="外貌",
                    hairstyle="发型",
                    outfit="服装",
                    signature_traits=["特征"],
                    personality="性格",
                    reference_image_prompt="立绘",
                ),
            ]
        )

    async def configured_model(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return config

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(character_handler, "generate_structured_text", generate_text)

    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        progress=5,
        request_data={"cast_mode": "append"},
    )
    result = await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    assert deleted == []
    assert existing.name == "陆沉"
    assert existing.version == 2
    assert existing.profile.get("role") == "男主"
    assert len(created) == 1
    assert created[0].name == "新人"
    assert result["character_ids"] == [str(created[0].id)]


@pytest.mark.asyncio
async def test_append_scene_cast_keeps_orphans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    existing = SceneRecord(project_id=project_id, name="旧客厅")
    existing.id = uuid4()
    existing.version = 3
    existing.status = "approved"
    existing.profile = {"description": "旧描述"}
    created: list[SceneRecord] = []
    deleted: list[UUID] = []
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="重生",
        synopsis="梗概",
        genre="都市",
        art_style="写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=None,
        image_model="qwen-image-test",
        image_base_url="https://image.example/v1",
    )

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ProjectRecord:
                return project
            return None

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [existing])

        def add(self, item: SceneRecord) -> None:
            if not getattr(item, "id", None):
                item.id = uuid4()
            created.append(item)

        async def delete(self, item: SceneRecord) -> None:
            deleted.append(item.id)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def generate_text(**kwargs: object) -> SceneGenerationOutput:
        return SceneGenerationOutput(
            scenes=[
                GeneratedScene(
                    name="旧客厅",
                    description="应跳过",
                    lighting="光",
                    palette="色",
                    visual_traits=["特征"],
                ),
                GeneratedScene(
                    name="新咖啡馆",
                    description="新描述",
                    lighting="暖光",
                    palette="木色",
                    visual_traits=["吧台"],
                ),
            ]
        )

    async def configured_model(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return config

    monkeypatch.setattr(scene_handler, "require_text_model", configured_model)
    monkeypatch.setattr(scene_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(scene_handler, "generate_structured_text", generate_text)

    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        progress=5,
        request_data={"cast_mode": "append"},
    )
    result = await scene_handler.generate_scenes(FakeSession(), task)  # type: ignore[arg-type]

    assert deleted == []
    assert existing.name == "旧客厅"
    assert existing.version == 3
    assert len(created) == 1
    assert created[0].name == "新咖啡馆"
    assert result["scene_ids"] == [str(created[0].id)]


@pytest.mark.asyncio
async def test_character_text_only_skips_images(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    character = CharacterRecord(project_id=project_id, status="draft", name="旧名")
    character.id = uuid4()
    character.version = 1
    character.profile = {"generation_source": "ai", "image_prompt": "旧提示", "role": "配角"}
    character.reference_asset_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="雨夜",
        synopsis="梗概",
        genre="悬疑",
        art_style="写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=b"image",
        image_model="qwen-image-test",
        image_base_url="https://image.example/v1",
    )

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            return project

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [character])

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def generate_text(**kwargs: object) -> CharacterGenerationOutput:
        return CharacterGenerationOutput(
            characters=[
                GeneratedCharacter(
                    name="新名",
                    role="主角",
                    appearance="外貌",
                    hairstyle="发型",
                    outfit="服装",
                    signature_traits=["特征"],
                    personality="性格",
                    reference_image_prompt="新立绘",
                )
            ]
        )

    async def configured_model(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return config

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(character_handler, "generate_structured_text", generate_text)

    async def unexpected_image(**kwargs: object) -> str:
        raise AssertionError("text_only must skip images")

    monkeypatch.setattr(character_handler, "generate_image", unexpected_image)

    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        progress=5,
        request_data={"character_ids": [str(character.id)], "text_only": True},
    )
    result = await character_handler.generate_characters(FakeSession(), task, text_only=True)  # type: ignore[arg-type]

    assert character.name == "新名"
    assert result["reference_images_generated"] == 0


@pytest.mark.asyncio
async def test_character_reference_images_run_with_limited_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="并行出图",
        synopsis="梗概",
        genre="悬疑",
        art_style="电影感写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text-encrypted",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=b"image-encrypted",
        image_base_url="https://image.example/v1",
        image_model="qwen-image-test",
    )
    created: list[CharacterRecord] = []
    in_flight = 0
    max_in_flight = 0

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            assert model is ProjectRecord
            return project

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [])

        def add(self, item: CharacterRecord) -> None:
            item.id = uuid4()
            created.append(item)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def configured_model(session: object, account_id: object) -> SimpleNamespace:
        return config

    async def generate_text(**kwargs: object) -> CharacterGenerationOutput:
        return CharacterGenerationOutput(
            characters=[
                GeneratedCharacter(
                    name=f"角色{index}",
                    role="配角",
                    appearance="外表",
                    hairstyle="发型",
                    outfit="服装",
                    signature_traits=["特征"],
                    personality="性格",
                    reference_image_prompt="全身立绘",
                )
                for index in range(1, 4)
            ]
        )

    async def generate_image(**kwargs: object) -> str:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        assert kwargs["prompt_extend"] is False
        return f"/api/v1/assets/{kwargs['asset_id']}"

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(character_handler, "generate_structured_text", generate_text)
    monkeypatch.setattr(character_handler, "generate_image", generate_image)
    monkeypatch.setattr(
        character_handler,
        "get_settings",
        lambda: SimpleNamespace(image_model_concurrency=2),
    )

    task = SimpleNamespace(id=uuid4(), project_id=project_id, progress=5, request_data={})
    result = await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    assert len(created) == 3
    assert result["reference_images_generated"] == 3
    assert max_in_flight == 2


@pytest.mark.asyncio
async def test_character_text_regen_clears_stale_image_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    character_id = uuid4()
    character = CharacterRecord(project_id=project_id, status="draft")
    character.id = character_id
    character.name = "旧角色"
    character.profile = {"generation_source": "ai", "image_prompt": "旧提示词"}
    character.version = 1
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="雨夜的旧车站",
        synopsis="梗概",
        genre="悬疑",
        art_style="电影感写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text-encrypted",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=b"image-encrypted",
        image_base_url="https://image.example/v1",
        image_model="qwen-image-test",
    )

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            assert model is ProjectRecord
            return project

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [character])

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def configured_model(session: object, account_id: object) -> SimpleNamespace:
        return config

    async def generate_text(**kwargs: object) -> CharacterGenerationOutput:
        return CharacterGenerationOutput(
            characters=[
                GeneratedCharacter(
                    name="新角色",
                    role="新设定",
                    appearance="新外貌",
                    hairstyle="短发",
                    outfit="新服装",
                    signature_traits=["新特征"],
                    personality="冷静",
                    reference_image_prompt="新参考图提示词",
                )
            ]
        )

    async def generate_image(**kwargs: object) -> str:
        assert kwargs.get("resume_task_id") is None
        assert "新参考图提示词" in str(kwargs["prompt"])
        return f"/api/v1/assets/{kwargs['asset_id']}"

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(character_handler, "generate_structured_text", generate_text)
    monkeypatch.setattr(character_handler, "generate_image", generate_image)

    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        progress=5,
        request_data={
            "cast_mode": "replace",
            "provider_jobs": {
                f"character:{character_id}": {
                    "asset_id": str(uuid4()),
                    "remote_task_id": "stale-remote",
                }
            },
        },
    )
    await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    jobs = task.request_data.get("provider_jobs", {})
    character_job = jobs.get(f"character:{character_id}")
    assert character_job is not None
    assert character_job.get("remote_task_id") != "stale-remote"
    assert character.name == "新角色"


@pytest.mark.asyncio
async def test_character_recoverable_image_error_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    character_id = uuid4()
    character = CharacterRecord(project_id=project_id, status="draft")
    character.id = character_id
    character.name = "沈知遥"
    character.profile = {"generation_source": "ai", "image_prompt": "提示词"}
    character.reference_asset_id = None
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="雨夜的旧车站",
        synopsis="梗概",
        genre="悬疑",
        art_style="电影感写实",
    )
    config = SimpleNamespace(
        text_api_key_encrypted=b"text-encrypted",
        text_base_url="https://text.example/v1",
        text_model="text-model",
        image_api_key_encrypted=b"image-encrypted",
        image_base_url="https://image.example/v1",
        image_model="qwen-image-test",
    )

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            if model is ProjectRecord:
                return project
            if model is CharacterRecord:
                return character
            raise AssertionError(f"Unexpected model: {model}")

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [character])

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def configured_model(session: object, account_id: object) -> SimpleNamespace:
        return config

    async def generate_image(**kwargs: object) -> str:
        raise RecoverableProviderError("查询 Qwen Image 任务失败（HTTP 429）")

    monkeypatch.setattr(character_handler, "require_text_model", configured_model)
    monkeypatch.setattr(character_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(
        character_handler,
        "generate_structured_text",
        lambda **_: (_ for _ in ()).throw(AssertionError("should use text checkpoint")),
    )
    monkeypatch.setattr(character_handler, "generate_image", generate_image)

    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        progress=5,
        request_data={
            "text_checkpoints": {
                "characters": {"done": True, "character_ids": [str(character_id)]}
            },
            "provider_jobs": {},
        },
    )
    with pytest.raises(RecoverableProviderError, match="429"):
        await character_handler.generate_characters(FakeSession(), task)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_scene_generation_persists_only_scene_profile_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    episode_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        title="雨夜旧车站",
        synopsis="修表师听见怀表里的求救声。",
        genre="悬疑",
        art_style="电影感写实",
    )
    episode = SimpleNamespace(synopsis=project.synopsis)
    created: list[SceneRecord] = []

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            if model is ProjectRecord:
                assert record_id == project_id
                return project
            if model is EpisodeRecord:
                assert record_id == episode_id
                return episode
            raise AssertionError(f"Unexpected model: {model}")

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [])

        def add(self, item: SceneRecord) -> None:
            item.id = uuid4()
            created.append(item)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    async def configured_model(session: object, account_id: object) -> SimpleNamespace:
        assert account_id == owner_id
        return SimpleNamespace(
            text_api_key_encrypted=b"encrypted",
            text_base_url="https://text.example/v1",
            text_model="text-model",
            image_api_key_encrypted=b"image-encrypted",
            image_model="qwen-image-test",
            image_base_url="https://image.example/v1",
        )

    async def generate_text(**kwargs: object) -> SceneGenerationOutput:
        assert kwargs["response_model"] is SceneGenerationOutput
        return SceneGenerationOutput(
            scenes=[
                GeneratedScene(
                    name="雨夜废弃站台",
                    description="雨水映出褪色站牌与远处的红色信号灯。",
                    lighting="冷色路灯和远处红光",
                    palette="蓝灰与暗红",
                    visual_traits=["湿润地面", "锈蚀铁轨"],
                )
            ]
        )

    async def generate_image(**kwargs: object) -> str:
        assert kwargs["model"] == "qwen-image-test"
        assert kwargs["prompt_extend"] is False
        assert "雨夜废弃站台" in str(kwargs["prompt"])
        return f"/api/v1/assets/{kwargs['asset_id']}"

    monkeypatch.setattr(scene_handler, "require_text_model", configured_model)
    monkeypatch.setattr(scene_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(scene_handler, "generate_structured_text", generate_text)
    monkeypatch.setattr(scene_handler, "generate_image", generate_image)

    task = SimpleNamespace(
        project_id=project_id,
        request_data={"episode_id": str(episode_id)},
        progress=5,
    )
    # ensure mutable request_data for provider job checkpoints
    result = await scene_handler.generate_scenes(FakeSession(), task)  # type: ignore[arg-type]

    assert result["scene_ids"] == [str(created[0].id)]
    assert created[0].name == "雨夜废弃站台"
    assert created[0].reference_asset_id is not None
    assert "name" not in created[0].profile
    assert SceneProfile.model_validate(created[0].profile).description
    assert result["reference_images_generated"] == 1
    assert result["warnings"] == []


@pytest.mark.asyncio
async def test_image_only_scene_generation_skips_text_and_renders_missing_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    scene = SimpleNamespace(
        id=uuid4(),
        name="旧车站",
        profile={
            "description": "深夜空无一人的旧车站。",
            "lighting": "冷白灯",
            "palette": "青灰色",
            "visual_traits": ["湿润地面"],
        },
        reference_asset_id=None,
    )
    project = SimpleNamespace(
        id=project_id,
        owner_id=owner_id,
        art_style="电影感写实",
    )
    config = SimpleNamespace(
        image_api_key_encrypted=b"encrypted",
        image_model="qwen-image-test",
        image_base_url="https://image.example/v1",
    )

    class FakeSession:
        async def get(self, model: type[object], record_id: object) -> object:
            if model is ProjectRecord:
                return project
            if model is AccountModelConfigRecord:
                return config
            raise AssertionError(f"Unexpected model: {model}")

        async def scalars(self, query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [scene])

        async def commit(self) -> None:
            pass

    async def generate_image(**kwargs: object) -> str:
        assert kwargs["asset_id"]
        assert "深夜空无一人的旧车站" in str(kwargs["prompt"])
        return "local-asset-url"

    async def unexpected_text(**kwargs: object) -> None:
        raise AssertionError("image-only generation must skip text provider")

    monkeypatch.setattr(scene_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(scene_handler, "generate_image", generate_image)
    monkeypatch.setattr(scene_handler, "generate_structured_text", unexpected_text)
    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        request_data={"image_only": True},
        progress=5,
    )

    result = await scene_handler.generate_scenes(FakeSession(), task, image_only=True)  # type: ignore[arg-type]

    assert scene.reference_asset_id is not None
    assert result["reference_images_generated"] == 1
    assert result["warnings"] == []


@pytest.mark.asyncio
async def test_scene_checkpoint_commit_failure_is_not_downgraded_to_image_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    scene = SimpleNamespace(
        id=uuid4(),
        name="旧车站",
        profile={"description": "深夜空无一人的旧车站。"},
        reference_asset_id=None,
    )
    project = SimpleNamespace(id=project_id, owner_id=owner_id, art_style="电影感写实")
    config = SimpleNamespace(
        image_api_key_encrypted=b"encrypted",
        image_model="qwen-image-test",
        image_base_url="https://image.example/v1",
    )

    class FakeSession:
        commits = 0

        async def get(self, model: type[object], _record_id: object) -> object:
            if model is ProjectRecord:
                return project
            if model is AccountModelConfigRecord:
                return config
            raise AssertionError(f"Unexpected model: {model}")

        async def scalars(self, _query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [scene])

        async def commit(self) -> None:
            self.commits += 1
            # bind_image_job persists the initial checkpoint first; the next
            # commit fences the provider call and must propagate on failure.
            if self.commits == 2:
                raise RuntimeError("database commit failed")

    async def unexpected_image(**_kwargs: object) -> str:
        raise AssertionError("provider must not be called before checkpoint commit")

    monkeypatch.setattr(scene_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(scene_handler, "generate_image", unexpected_image)
    task = SimpleNamespace(id=uuid4(), project_id=project_id, request_data={}, progress=5)

    with pytest.raises(RuntimeError, match="database commit failed"):
        await scene_handler.generate_scenes(
            FakeSession(),
            task,
            image_only=True,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_unexpected_scene_provider_error_keeps_task_failed_and_checkpointed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = uuid4()
    owner_id = uuid4()
    scene = SimpleNamespace(
        id=uuid4(),
        name="旧车站",
        profile={"description": "深夜空无一人的旧车站。"},
        reference_asset_id=None,
    )
    project = SimpleNamespace(id=project_id, owner_id=owner_id, art_style="电影感写实")
    config = SimpleNamespace(
        image_api_key_encrypted=b"encrypted",
        image_model="qwen-image-test",
        image_base_url="https://image.example/v1",
    )
    task = SimpleNamespace(id=uuid4(), project_id=project_id, request_data={}, progress=5)

    class FakeSession:
        async def get(self, model: type[object], _record_id: object) -> object:
            if model is ProjectRecord:
                return project
            if model is AccountModelConfigRecord:
                return config
            raise AssertionError(f"Unexpected model: {model}")

        async def scalars(self, _query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [scene])

        async def commit(self) -> None:
            return None

    async def unexpected_image(**kwargs: object) -> str:
        on_submit_started = kwargs["on_submit_started"]
        assert callable(on_submit_started)
        await on_submit_started()
        raise RuntimeError("unexpected provider failure")

    monkeypatch.setattr(scene_handler, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(scene_handler, "generate_image", unexpected_image)

    with pytest.raises(RuntimeError, match="unexpected provider failure"):
        await scene_handler.generate_scenes(
            FakeSession(),
            task,
            image_only=True,  # type: ignore[arg-type]
        )

    checkpoint = task.request_data["provider_jobs"][f"scene:{scene.id}"]
    assert checkpoint["submission_state"] == "submitting"
    assert scene.reference_asset_id is None
