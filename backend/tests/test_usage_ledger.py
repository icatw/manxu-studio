import json
import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel

from app.core.correlation import (
    clear_correlation,
    set_account_id,
    set_request_id,
    stamp_request_correlation,
)
from app.core.logging import JsonLogFormatter
from app.db.models import GenerationTaskRecord
from app.providers import image_dispatch, openai_compatible
from app.providers.openai_compatible import generate_structured_text
from app.services import generations as generations_service
from app.services import usage as usage_service


class _SampleModel(BaseModel):
    title: str


def test_json_log_formatter_includes_task_and_usage_fields() -> None:
    record = logging.LogRecord(
        "manxu.api",
        logging.INFO,
        __file__,
        1,
        "provider_call_succeeded",
        (),
        None,
    )
    record.event = "provider_call_succeeded"
    record.request_id = "req-1"
    record.task_id = "task-1"
    record.account_id = "acct-1"
    record.prompt_tokens = 10
    record.completion_tokens = 20
    record.total_tokens = 30
    record.billable = True
    record.outcome = "success"
    record.call_kind = "text"
    record.model = "demo-model"
    line = JsonLogFormatter().format(record)
    output = json.loads(line)
    assert output["task_id"] == "task-1"
    assert output["account_id"] == "acct-1"
    assert output["prompt_tokens"] == 10
    assert output["billable"] is True
    assert output["outcome"] == "success"


def test_stamp_request_correlation_merges_request_id() -> None:
    clear_correlation()
    set_request_id("http-req-99")
    stamped = stamp_request_correlation({"foo": "bar"})
    assert stamped["foo"] == "bar"
    assert stamped["_correlation"] == {"request_id": "http-req-99"}
    clear_correlation()


@pytest.mark.asyncio
async def test_create_task_stamps_correlation(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_correlation()
    set_request_id("create-req-1")
    owner_id = uuid4()
    project_id = uuid4()
    added: list[GenerationTaskRecord] = []

    class FakeSession:
        async def scalar(self, query: object) -> object | None:
            return None

        def add(self, obj: object) -> None:
            if isinstance(obj, GenerationTaskRecord):
                if obj.id is None:
                    obj.id = uuid4()
                obj.created_at = datetime.now(UTC)
                obj.updated_at = datetime.now(UTC)
                added.append(obj)

        async def commit(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            pass

    async def fake_enqueue(task_id: object, *, reclaim_if_blocked: bool = False) -> bool:
        del task_id, reclaim_if_blocked
        return True

    monkeypatch.setattr(generations_service, "enqueue_generation_task", fake_enqueue)
    view = await generations_service.create_task(
        FakeSession(),  # type: ignore[arg-type]
        owner_id=owner_id,
        project_id=project_id,
        task_type="storyboard_draft",
        request_data={"source": "test"},
    )
    assert len(added) == 1
    assert added[0].request_data["_correlation"] == {"request_id": "create-req-1"}
    assert view.id == added[0].id
    clear_correlation()


@pytest.mark.asyncio
async def test_generate_structured_text_records_usage_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_correlation()
    account_id = uuid4()
    set_account_id(account_id)
    set_request_id("text-req-1")
    captured: list[dict[str, object]] = []

    async def capture_usage(**kwargs: object) -> SimpleNamespace:
        captured.append(dict(kwargs))
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(openai_compatible, "record_usage_event", capture_usage)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"title":"ok"}'}}],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 22,
                    "total_tokens": 33,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self: httpx.AsyncClient, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)

    result = await generate_structured_text(
        base_url="https://example.com/v1",
        model="demo-text",
        api_key="secret",
        system_prompt="sys",
        user_prompt="user",
        response_model=_SampleModel,
    )
    assert result.title == "ok"
    assert len(captured) == 1
    assert captured[0]["call_kind"] == "text"
    assert captured[0]["outcome"] == "success"
    assert captured[0]["prompt_tokens"] == 11
    assert captured[0]["completion_tokens"] == 22
    assert captured[0]["total_tokens"] == 33
    assert captured[0]["provider"] == "openai_compatible"
    clear_correlation()


@pytest.mark.asyncio
async def test_generate_structured_text_records_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_correlation()
    set_account_id(uuid4())
    captured: list[dict[str, object]] = []

    async def capture_usage(**kwargs: object) -> None:
        captured.append(dict(kwargs))

    monkeypatch.setattr(openai_compatible, "record_usage_event", capture_usage)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self: httpx.AsyncClient, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)

    with pytest.raises(ValueError):
        await generate_structured_text(
            base_url="https://example.com/v1",
            model="demo-text",
            api_key="secret",
            system_prompt="sys",
            user_prompt="user",
            response_model=_SampleModel,
        )
    assert len(captured) == 1
    assert captured[0]["outcome"] == "failed"
    assert captured[0].get("error_code") == "ValueError"
    clear_correlation()


@pytest.mark.asyncio
async def test_generate_image_records_image_units(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_correlation()
    set_account_id(uuid4())
    captured: list[dict[str, object]] = []

    async def capture_usage(**kwargs: object) -> None:
        captured.append(dict(kwargs))

    async def fake_generate(**kwargs: object) -> str:
        del kwargs
        return "/api/v1/assets/demo"

    monkeypatch.setattr(image_dispatch, "record_usage_event", capture_usage)
    monkeypatch.setattr(image_dispatch.default_qwen_image_provider, "generate", fake_generate)

    url = await image_dispatch.generate_image(
        api_key="key",
        model="qwen-image",
        prompt="a panel",
        asset_id=uuid4(),
        image_backend="qwen_async",
    )
    assert url == "/api/v1/assets/demo"
    assert len(captured) == 1
    assert captured[0]["call_kind"] == "image"
    assert captured[0]["outcome"] == "success"
    assert captured[0]["image_units"] == 1
    assert captured[0]["provider"] == "qwen_async"
    clear_correlation()


@pytest.mark.asyncio
async def test_record_usage_event_skips_without_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_correlation()
    calls: list[object] = []

    class BoomSession:
        def __init__(self) -> None:
            calls.append("opened")

        async def __aenter__(self) -> "BoomSession":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        def add(self, obj: object) -> None:
            raise AssertionError("should not persist")

    monkeypatch.setattr(usage_service, "SessionFactory", BoomSession)
    result = await usage_service.record_usage_event(
        call_kind="text",
        provider="openai_compatible",
        model="m",
        outcome="success",
        prompt_tokens=1,
    )
    assert result is None
    assert calls == []
