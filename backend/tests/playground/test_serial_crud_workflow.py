from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from tests.playground.conftest import unwrap

pytestmark = pytest.mark.playground


@pytest.mark.asyncio
async def test_project_bible_threads_episodes_continuity(
    api_client: httpx.AsyncClient,
    login_account: Callable[[str], Awaitable[dict[str, Any]]],
    unique_email: Callable[[], str],
) -> None:
    await login_account(unique_email())

    created = await api_client.post(
        "/projects",
        json={
            "title": "雾港来信",
            "synopsis": "港口迷雾中的信件与失踪的灯塔看守人。",
            "genre": "悬疑",
            "art_style": "电影感写实",
            "aspect_ratio": "portrait",
        },
    )
    assert created.status_code == 201, created.text
    project = unwrap(created.json())
    project_id = project["id"]

    bible = await api_client.patch(
        f"/projects/{project_id}",
        json={
            "world_setting": "雾港常年被海雾笼罩。",
            "style_rules": "冷色调、细雨质感。",
            "negative_prompt": "文字水印",
            "style_seed": 42,
        },
    )
    assert bible.status_code == 200, bible.text
    bible_data = unwrap(bible.json())
    assert bible_data["project"]["world_setting"] == "雾港常年被海雾笼罩。"
    assert bible_data["project"]["style_seed"] == 42
    assert bible_data["impact"]["reason"] == "bible_visual"
    assert "style_rules" in bible_data["impact"]["changed_fields"]

    thread = await api_client.post(
        f"/projects/{project_id}/plot-threads",
        json={"text": "灯塔看守人留下的未拆信件。", "resolved": False},
    )
    assert thread.status_code == 201, thread.text
    thread_id = unwrap(thread.json())["id"]

    threads = await api_client.get(f"/projects/{project_id}/plot-threads")
    assert threads.status_code == 200
    assert any(item["id"] == thread_id for item in unwrap(threads.json()))

    episode = await api_client.post(
        f"/projects/{project_id}/episodes",
        json={"title": "第 1 话", "synopsis": "来信抵达雾港。", "panel_count": 4},
    )
    assert episode.status_code == 201, episode.text
    episode_id = unwrap(episode.json())["id"]

    episodes = await api_client.get(f"/projects/{project_id}/episodes")
    assert episodes.status_code == 200
    assert any(item["id"] == episode_id for item in unwrap(episodes.json()))

    continuity = await api_client.get(f"/projects/{project_id}/continuity")
    assert continuity.status_code == 200
    continuity_data = unwrap(continuity.json())
    assert "雾港" in continuity_data["world_setting"]
    assert any(item["id"] == thread_id for item in continuity_data["open_threads"])

    deleted = await api_client.delete(f"/projects/{project_id}")
    assert deleted.status_code in {200, 204}

    missing = await api_client.get(f"/projects/{project_id}")
    assert missing.status_code == 404
