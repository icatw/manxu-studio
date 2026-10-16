"""PAGE A1 layout bootstrap/sync against playground Postgres."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tests.playground.conftest import unwrap, wait_for_login_code

pytestmark = pytest.mark.playground


async def _create_panel(client: httpx.AsyncClient, episode_id: str, label: int) -> dict[str, Any]:
    response = await client.post(
        f"/episodes/{episode_id}/panels",
        json={
            "scene_description": f"场景 {label}",
            "shot": "中景",
            "composition": "居中",
            "character_actions": "站立",
            "emotion": "平静",
            "dialogue": f"对白 {label}",
            "story_purpose": "推进",
            "image_prompt": "test panel",
        },
    )
    assert response.status_code == 201, response.text
    return unwrap(response.json())


@pytest.mark.asyncio
async def test_layout_bootstrap_sync_and_foreign_404(
    playground_base_url: str,
    mailpit_base_url: str,
    unique_email: Callable[[], str],
) -> None:
    email_a = unique_email()
    email_b = unique_email()

    async with httpx.AsyncClient(
        base_url=f"{playground_base_url}/api/v1",
        timeout=60.0,
        trust_env=False,
    ) as client_a:
        assert (await client_a.post("/auth/email/code", json={"email": email_a})).status_code == 202
        verify_a = await client_a.post(
            "/auth/email/verify",
            json={"email": email_a, "code": await wait_for_login_code(mailpit_base_url, email_a)},
        )
        assert verify_a.status_code == 200
        csrf_a = unwrap((await client_a.get("/auth/csrf")).json())["token"]
        client_a.headers["X-CSRF-Token"] = csrf_a

        created = await client_a.post(
            "/projects",
            json={
                "title": "竖条排版验收",
                "synopsis": "用于 layout bootstrap/sync。",
                "genre": "日常",
                "art_style": "简洁线稿",
                "aspect_ratio": "portrait",
            },
        )
        assert created.status_code == 201, created.text
        project_id = unwrap(created.json())["id"]

        episode = await client_a.post(
            f"/projects/{project_id}/episodes",
            json={"title": "第 1 话", "synopsis": "开场。", "panel_count": 4},
        )
        assert episode.status_code == 201, episode.text
        episode_id = unwrap(episode.json())["id"]

        panel_a = await _create_panel(client_a, episode_id, 1)
        panel_b = await _create_panel(client_a, episode_id, 2)

        empty = await client_a.get(f"/episodes/{episode_id}/layout")
        assert empty.status_code == 200, empty.text
        assert unwrap(empty.json())["pages"] == []

        bootstrap = await client_a.post(
            f"/episodes/{episode_id}/layout/bootstrap",
            json={"default_height_px": 700, "default_gap_px": 20},
        )
        assert bootstrap.status_code == 201, bootstrap.text
        layout = unwrap(bootstrap.json())
        assert len(layout["pages"]) == 1
        assert [slot["panel_id"] for slot in layout["pages"][0]["slots"]] == [
            panel_a["id"],
            panel_b["id"],
        ]

        conflict = await client_a.post(f"/episodes/{episode_id}/layout/bootstrap", json={})
        assert conflict.status_code == 409

        panel_c = await _create_panel(client_a, episode_id, 3)
        synced = await client_a.post(
            f"/episodes/{episode_id}/layout/sync",
            json={"follow_current_version": True},
        )
        assert synced.status_code == 200, synced.text
        slot_panel_ids = [slot["panel_id"] for slot in unwrap(synced.json())["pages"][0]["slots"]]
        assert panel_c["id"] in slot_panel_ids
        assert len(slot_panel_ids) == 3

    async with httpx.AsyncClient(
        base_url=f"{playground_base_url}/api/v1",
        timeout=60.0,
        trust_env=False,
    ) as client_b:
        assert (await client_b.post("/auth/email/code", json={"email": email_b})).status_code == 202
        verify_b = await client_b.post(
            "/auth/email/verify",
            json={"email": email_b, "code": await wait_for_login_code(mailpit_base_url, email_b)},
        )
        assert verify_b.status_code == 200
        csrf_b = unwrap((await client_b.get("/auth/csrf")).json())["token"]
        client_b.headers["X-CSRF-Token"] = csrf_b

        foreign_get = await client_b.get(f"/episodes/{episode_id}/layout")
        assert foreign_get.status_code == 404
        foreign_bootstrap = await client_b.post(
            f"/episodes/{episode_id}/layout/bootstrap",
            json={},
        )
        assert foreign_bootstrap.status_code == 404
        foreign_sync = await client_b.post(f"/episodes/{episode_id}/layout/sync", json={})
        assert foreign_sync.status_code == 404
