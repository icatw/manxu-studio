from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import (
    AccountModelConfigRecord,
    CharacterRecord,
    EpisodeRecord,
    ProjectRecord,
    SceneRecord,
)
from app.schemas.workspace import SceneProfile
from app.services import workspace_tasks
from app.services.workspace_tasks import (
    CharacterGenerationOutput,
    GeneratedCharacter,
    GeneratedPanel,
    GeneratedScene,
    SceneGenerationOutput,
    StoryboardGenerationOutput,
    _generate_characters,
    _generate_panels,
    _generate_scenes,
)


@pytest.mark.asyncio
async def test_storyboard_replacement_flushes_deletes_before_inserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    episode_id = uuid4()
    project_id = uuid4()
    existing_panel = object()
    episode = SimpleNamespace(synopsis="A story")
    project = SimpleNamespace(owner_id=uuid4(), title="Title", genre="幻想", art_style="漫画")
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

    monkeypatch.setattr(workspace_tasks, "_configured_model", configured_model)
    monkeypatch.setattr(workspace_tasks, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(workspace_tasks, "generate_structured_text", generate_text)

    task = SimpleNamespace(
        request_data={"episode_id": str(episode_id), "panel_count": 1},
        project_id=project_id,
    )

    result = await _generate_panels(FakeSession(), task)  # type: ignore[arg-type]

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
            character=GeneratedCharacter(
                name="沈知遥",
                role="表行学徒，能通过修表回放物件最后一次滴答",
                appearance="二十六岁，清瘦，左眉有一道被玻璃划出的浅疤。",
                hairstyle="齐耳黑发，雨水打湿后贴在脸侧。",
                outfit="旧深绿工装外套，袖口缝着银线。",
                signature_traits=["停摆的怀表", "左眉浅疤"],
                personality="克制多疑，遇到失踪儿童线索时会冒险追查。",
                reference_image_prompt="全身角色立绘，深绿工装外套，银线袖口，左眉浅疤。",
            )
        )

    async def generate_image(**kwargs: object) -> str:
        calls.append(("image", kwargs))
        assert kwargs["model"] == config.image_model
        assert kwargs["base_url"] == config.image_base_url
        assert "沈知遥" in str(kwargs["prompt"])
        return "/api/v1/assets/generated.png"

    monkeypatch.setattr(workspace_tasks, "_configured_model", configured_model)
    monkeypatch.setattr(
        workspace_tasks,
        "decrypt_secret",
        lambda encrypted: (
            "decrypted-text-key"
            if encrypted == b"text-encrypted"
            else "decrypted-image-key"
        ),
    )
    monkeypatch.setattr(workspace_tasks, "generate_structured_text", generate_text)
    monkeypatch.setattr(workspace_tasks, "generate_qwen_image", generate_image)

    task = SimpleNamespace(id=task_id, project_id=project_id, progress=5)
    result = await _generate_characters(FakeSession(), task)  # type: ignore[arg-type]

    assert [name for name, _ in calls] == ["text", "image"]
    assert len(created) == 1
    assert created[0].name == "沈知遥"
    assert created[0].profile["generation_source"] == "ai"
    assert created[0].reference_asset_id == dict(calls[1][1])["asset_id"]
    assert result["generation_source"] == "ai"
    assert result["reference_image_generated"] is True
    assert progress == sorted(progress)
    assert progress[-1] == 95


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
        assert "雨夜废弃站台" in str(kwargs["prompt"])
        return f"/api/v1/assets/{kwargs['asset_id']}"

    monkeypatch.setattr(workspace_tasks, "_configured_model", configured_model)
    monkeypatch.setattr(workspace_tasks, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(workspace_tasks, "generate_structured_text", generate_text)
    monkeypatch.setattr(workspace_tasks, "generate_qwen_image", generate_image)

    task = SimpleNamespace(
        project_id=project_id,
        request_data={"episode_id": str(episode_id)},
        progress=5,
    )
    result = await _generate_scenes(FakeSession(), task)  # type: ignore[arg-type]

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

    monkeypatch.setattr(workspace_tasks, "decrypt_secret", lambda _: "secret")
    monkeypatch.setattr(workspace_tasks, "generate_qwen_image", generate_image)
    monkeypatch.setattr(workspace_tasks, "generate_structured_text", unexpected_text)
    task = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        request_data={"image_only": True},
        progress=5,
    )

    result = await _generate_scenes(FakeSession(), task, image_only=True)  # type: ignore[arg-type]

    assert scene.reference_asset_id is not None
    assert result["reference_images_generated"] == 1
    assert result["warnings"] == []
