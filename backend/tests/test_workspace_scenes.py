from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.security import require_asset_owner
from app.db.models import ExportRecord, ProjectRecord
from app.schemas.workspace import SceneProfile
from app.services.assets import scene_view


def test_scene_view_ignores_legacy_name_in_json_profile() -> None:
    record = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        name="雨夜废弃站台",
        profile={
            "name": "雨夜废弃站台",
            "description": "暴雨中的旧站台，地面映出残缺路灯。",
            "lighting": "冷色路灯",
            "palette": "蓝灰与暗红",
            "visual_traits": ["湿润地面", "锈蚀铁轨"],
        },
        reference_asset_id=None,
        status="draft",
        version=1,
    )

    scene = scene_view(record)  # type: ignore[arg-type]

    assert scene.name == "雨夜废弃站台"
    assert SceneProfile.model_validate(scene.profile).description


@pytest.mark.asyncio
@pytest.mark.parametrize("is_owner", [True, False])
async def test_scene_reference_asset_access_is_project_scoped(is_owner: bool) -> None:
    owner_id = uuid4()
    account_id = owner_id if is_owner else uuid4()
    project_id = uuid4()
    asset_id = uuid4()
    project = SimpleNamespace(id=project_id, owner_id=owner_id)
    scene = SimpleNamespace(id=uuid4(), project_id=project_id, reference_asset_id=asset_id)

    class FakeSession:
        def __init__(self) -> None:
            self.scalar_results = iter([None, None, scene])

        async def scalar(self, query: object) -> object | None:
            return next(self.scalar_results)

        async def get(self, model: type[object], record_id: object) -> object | None:
            if model is ExportRecord:
                return None
            assert model is ProjectRecord
            assert record_id == project_id
            return project

    if is_owner:
        assert (
            await require_asset_owner(
                asset_id,
                SimpleNamespace(id=account_id),  # type: ignore[arg-type]
                FakeSession(),  # type: ignore[arg-type]
            )
            == asset_id
        )
        return

    with pytest.raises(HTTPException) as error:
        await require_asset_owner(
            asset_id,
            SimpleNamespace(id=account_id),  # type: ignore[arg-type]
            FakeSession(),  # type: ignore[arg-type]
        )
    assert error.value.status_code == 404
