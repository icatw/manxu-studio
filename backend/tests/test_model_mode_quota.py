"""MODEL-04 / QUOTA-01 unit coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.model_modes import billing_source_for_mode, normalize_model_mode
from app.services import model_config as model_config_service
from app.services.platform_quota import (
    enforce_platform_quota_before_enqueue,
    quota_status_for_account,
    shanghai_day_bounds,
)
from app.tasks.support import ResolvedModelConfig, resolve_model_config


def test_normalize_and_billing_source() -> None:
    assert normalize_model_mode("platform") == "platform"
    assert normalize_model_mode("weird") == "byok_qwen"
    assert billing_source_for_mode("platform") == "platform"
    assert billing_source_for_mode("byok_agnes") == "byok"


def test_shanghai_day_bounds_cover_local_midnight() -> None:
    # 2026-10-21 16:00 UTC == 2026-10-22 00:00 Asia/Shanghai
    start, end = shanghai_day_bounds(datetime(2026, 10, 21, 16, 0, tzinfo=UTC))
    assert start == datetime(2026, 10, 21, 16, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 22, 16, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_quota_status_byok_does_not_apply() -> None:
    class FakeSession:
        async def scalar(self, _query: object) -> int:
            return 99

    status = await quota_status_for_account(
        FakeSession(),  # type: ignore[arg-type]
        uuid4(),
        model_mode="byok_qwen",
    )
    assert status["applies"] is False
    assert status["exhausted"] is False


@pytest.mark.asyncio
async def test_enforce_rejects_platform_when_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account_id = uuid4()

    class FakeSession:
        async def get(self, _model: type[object], _id: object) -> object:
            return SimpleNamespace(model_mode="platform")

        async def scalars(self, _query: object) -> SimpleNamespace:
            return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(
        "app.services.platform_quota.get_settings",
        lambda: SimpleNamespace(
            platform_available=True,
            platform_quota_text_per_day=10,
            platform_quota_image_per_day=10,
            platform_max_running_tasks=8,
        ),
    )

    async def fake_quota(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "applies": True,
            "text_remaining": 0,
            "image_remaining": 5,
            "exhausted": True,
            "message": "平台试用额度已用尽，请在设置中改用通义百炼或自备 Agnes。",
        }

    monkeypatch.setattr("app.services.platform_quota.quota_status_for_account", fake_quota)
    with pytest.raises(HTTPException) as raised:
        await enforce_platform_quota_before_enqueue(FakeSession(), account_id)  # type: ignore[arg-type]
    assert raised.value.status_code == 402


@pytest.mark.asyncio
async def test_resolve_platform_uses_settings_key(monkeypatch: pytest.MonkeyPatch) -> None:
    account_id = uuid4()

    async def fake_get_or_create(_session: object, _account_id: object) -> SimpleNamespace:
        return SimpleNamespace(model_mode="platform")

    monkeypatch.setattr(model_config_service, "get_or_create_config", fake_get_or_create)
    monkeypatch.setattr(
        "app.tasks.support.get_settings",
        lambda: SimpleNamespace(
            platform_available=True,
            platform_agnes_api_key="platform-secret",
            platform_agnes_text_base_url="https://apihub.agnes-ai.com/v1",
            platform_agnes_image_base_url="https://apihub.agnes-ai.com/v1",
            platform_agnes_text_model="agnes-3.0-flash",
            platform_agnes_image_model="agnes-image-2.5-flash",
        ),
    )
    monkeypatch.setattr("app.tasks.support.encrypt_secret", lambda raw: f"enc:{raw}".encode())

    resolved = await resolve_model_config(SimpleNamespace(), account_id)  # type: ignore[arg-type]
    assert isinstance(resolved, ResolvedModelConfig)
    assert resolved.model_mode == "platform"
    assert resolved.billing_source == "platform"
    assert resolved.text_model == "agnes-3.0-flash"
    assert resolved.text_api_key_encrypted == b"enc:platform-secret"


@pytest.mark.asyncio
async def test_update_rejects_platform_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        model_config_service,
        "get_settings",
        lambda: SimpleNamespace(platform_available=False),
    )
    with pytest.raises(HTTPException) as raised:
        await model_config_service.update_model_config(
            SimpleNamespace(),  # type: ignore[arg-type]
            uuid4(),
            model_config_service.ModelConfigUpdate(model_mode="platform"),
        )
    assert raised.value.status_code == 422
