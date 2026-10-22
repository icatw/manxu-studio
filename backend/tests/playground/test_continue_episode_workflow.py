"""Live playground verification for SERIAL-AGENT-01 continue orchestration."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from tests.playground.conftest import unwrap

pytestmark = pytest.mark.playground


async def _wait_task(
    client: httpx.AsyncClient, task_id: str, *, timeout: float = 90.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = await client.get(f"/generation-tasks/{task_id}")
        assert response.status_code == 200, response.text
        task = unwrap(response.json())
        if task["status"] in {"succeeded", "failed"}:
            return task
        await asyncio.sleep(0.5)
    raise TimeoutError(f"task {task_id} did not finish")


@pytest.mark.asyncio
async def test_continue_episode_gate_create_and_storyboard(
    api_client: httpx.AsyncClient,
    login_account: Callable[[str], Awaitable[dict[str, Any]]],
    unique_email: Callable[[], str],
    fake_llm_url: str,
) -> None:
    await login_account(unique_email())

    # Playground ships PLATFORM_AGNES_* → fake-llm; new accounts default to platform mode.
    config = unwrap((await api_client.get("/model-config")).json())
    assert config["model_mode"] == "platform"
    assert config["platform_available"] is True
    _ = fake_llm_url

    created = await api_client.post(
        "/projects",
        json={
            "title": "续写编排手验",
            "synopsis": "港口迷雾中的下一封信。",
            "genre": "悬疑",
            "art_style": "电影感写实",
            "aspect_ratio": "portrait",
        },
    )
    assert created.status_code == 201, created.text
    project_id = unwrap(created.json())["id"]

    bible = await api_client.patch(
        f"/projects/{project_id}",
        json={
            "world_setting": (
                "雾港。\n\n## 规划话大纲\n"
                "1. 来信抵达\n2. 灯塔夜探\n3. 迷雾真相"
            ),
        },
    )
    assert bible.status_code == 200, bible.text

    episode = await api_client.post(
        f"/projects/{project_id}/episodes",
        json={"title": "第 1 话", "synopsis": "来信抵达雾港。", "panel_count": 4},
    )
    assert episode.status_code == 201, episode.text
    ep1_id = unwrap(episode.json())["id"]

    # No summary → frontier blocks continue.
    blocked = await api_client.post(
        f"/projects/{project_id}/continue-episode-generations",
        json={"generate_storyboard": False, "panel_count": 4},
    )
    assert blocked.status_code == 409, blocked.text

    patch = await api_client.patch(
        f"/episodes/{ep1_id}",
        json={"summary": "旅人收到未拆信件，雾港灯塔方向传来钟声。"},
    )
    assert patch.status_code == 200, patch.text

    # Create-only continue.
    queued = await api_client.post(
        f"/projects/{project_id}/continue-episode-generations",
        json={"generate_storyboard": False, "panel_count": 4},
    )
    assert queued.status_code == 202, queued.text
    task = await _wait_task(api_client, unwrap(queued.json())["id"])
    assert task["status"] == "succeeded", task
    result = task["result"]
    assert result["created"] is True
    assert result["generate_storyboard"] is False
    assert result["panel_ids"] == []
    ep2_id = result["episode_id"]
    assert ep2_id != ep1_id

    episodes = unwrap((await api_client.get(f"/projects/{project_id}/episodes")).json())
    assert len(episodes) == 2
    ep2 = next(item for item in episodes if item["id"] == ep2_id)
    assert ep2["title"]
    assert ep2["synopsis"]

    # Mark ep2 summarized, then continue with storyboard.
    patch2 = await api_client.patch(
        f"/episodes/{ep2_id}",
        json={"summary": "灯塔夜探发现看守人的日志与未灭的油灯。"},
    )
    assert patch2.status_code == 200, patch2.text

    queued2 = await api_client.post(
        f"/projects/{project_id}/continue-episode-generations",
        json={"generate_storyboard": True, "panel_count": 4, "use_continuity": True},
    )
    assert queued2.status_code == 202, queued2.text
    task2 = await _wait_task(api_client, unwrap(queued2.json())["id"], timeout=120.0)
    assert task2["status"] == "succeeded", task2
    result2 = task2["result"]
    assert result2["generate_storyboard"] is True
    assert len(result2["panel_ids"]) >= 1
    ep3_id = result2["episode_id"]

    panels = unwrap((await api_client.get(f"/episodes/{ep3_id}/panels")).json())
    assert len(panels) == len(result2["panel_ids"])

    await api_client.delete(f"/projects/{project_id}")
