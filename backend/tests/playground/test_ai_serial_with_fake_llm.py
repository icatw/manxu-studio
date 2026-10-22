from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from tests.playground.conftest import unwrap

pytestmark = pytest.mark.playground


@pytest.mark.asyncio
async def test_plan_from_plan_and_summary_via_fake_llm(
    api_client: httpx.AsyncClient,
    login_account: Callable[[str], Awaitable[dict[str, Any]]],
    unique_email: Callable[[], str],
    fake_llm_url: str,
) -> None:
    await login_account(unique_email())

    # Use platform default (operator Agnes → fake-llm in playground).
    config = unwrap((await api_client.get("/model-config")).json())
    assert config["model_mode"] == "platform"
    _ = fake_llm_url

    plan = await api_client.post(
        "/projects/plan",
        json={
            "premise": "漂浮图书馆收集失踪旅人的梦境。",
            "genre": "奇幻",
            "art_style": "国风玄幻",
            "audience": "年轻成人",
            "chapter_count": 3,
            "aspect_ratio": "portrait",
        },
    )
    assert plan.status_code == 200, plan.text
    draft = unwrap(plan.json())
    assert draft["title"]
    assert len(draft["chapters"]) == 3
    assert draft["world_setting"]

    created = await api_client.post("/projects/from-plan", json=draft)
    assert created.status_code == 201, created.text
    result = unwrap(created.json())
    project_id = result["project"]["id"]
    episode_ids = result["episode_ids"]
    # SERIAL-01: only chapter 1 is materialized; remaining outline lives in world_setting.
    assert len(episode_ids) == 1
    assert "规划话大纲" in (result["project"].get("world_setting") or "")

    summary = await api_client.post(f"/episodes/{episode_ids[0]}/summary")
    assert summary.status_code == 200, summary.text
    summary_data = unwrap(summary.json())
    assert summary_data["summary"]
    assert summary_data["episode_id"] == episode_ids[0]

    episodes = await api_client.get(f"/projects/{project_id}/episodes")
    assert episodes.status_code == 200
    first = next(item for item in unwrap(episodes.json()) if item["id"] == episode_ids[0])
    assert first["summary"] == summary_data["summary"]

    await api_client.delete(f"/projects/{project_id}")
