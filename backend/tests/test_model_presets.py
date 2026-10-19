"""Server model presets and image-backend allowlists."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.model_presets import parse_system_presets
from app.db.models import AccountModelConfigRecord
from app.services.model_config import config_view


def test_default_presets_include_agnes_and_qwen() -> None:
    presets = parse_system_presets("")
    ids = {item.id for item in presets}
    assert "dashscope-default" in ids
    assert "agnes-default" in ids
    agnes = next(item for item in presets if item.id == "agnes-default")
    assert agnes.image_backend == "openai_images"


def test_custom_presets_from_json() -> None:
    raw = json.dumps(
        [
            {
                "id": "custom",
                "label": "Custom",
                "text_base_url": "https://example.com/v1",
                "image_base_url": "https://example.com/v1",
                "text_model": "t",
                "image_model": "i",
                "image_backend": "openai_images",
            }
        ]
    )
    presets = parse_system_presets(raw)
    assert len(presets) == 1
    assert presets[0].id == "custom"


def test_invalid_presets_raise() -> None:
    with pytest.raises(ValueError):
        parse_system_presets("{not-json")


def test_settings_image_models_for_backend() -> None:
    settings = Settings(
        image_model_allowlist="qwen-a,qwen-b",
        openai_image_model_allowlist="agnes-x",
    )
    assert settings.image_models_for_backend("qwen_async") == ["qwen-a", "qwen-b"]
    assert settings.image_models_for_backend("openai_images") == ["agnes-x"]


def test_config_view_exposes_backend_options() -> None:
    record = AccountModelConfigRecord(
        account_id=uuid4(),
        text_model="qwen-plus",
        text_base_url="https://example.com/v1",
        text_status="not_configured",
        image_model="qwen-image-3.0",
        image_backend="qwen_async",
        image_base_url="https://dashscope.aliyuncs.com/api/v1",
        image_status="not_configured",
    )
    view = config_view(record)
    assert view.image_backend == "qwen_async"
    assert view.image_provider == "qwen_async"
    assert any(item.id == "openai_images" for item in view.image_backends)
    assert any(item.id == "agnes-default" for item in view.system_presets)
