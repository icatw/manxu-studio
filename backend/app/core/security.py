import asyncio
import base64
import hashlib
import hmac
import ipaddress
import socket
from typing import Annotated, cast
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_responses import ApiError
from app.core.config import get_settings
from app.db.models import (
    AccountRecord,
    AccountSessionRecord,
    CharacterRecord,
    EpisodeRecord,
    ExportRecord,
    GenerationTaskRecord,
    ImageVersionRecord,
    PanelRecord,
    ProjectRecord,
    SceneRecord,
)
from app.db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def encrypt_secret(secret: str) -> bytes:
    key_source = get_settings().model_encryption_key
    if len(key_source) < 32:
        raise ApiError(
            "SERVICE_UNAVAILABLE",
            "服务端未配置模型密钥加密主密钥，请联系管理员。",
            status_code=503,
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(key_source.encode()).digest())
    return Fernet(key).encrypt(secret.encode())


def decrypt_secret(ciphertext: bytes | None) -> str:
    if not ciphertext:
        return ""
    key_source = get_settings().model_encryption_key
    if len(key_source) < 32:
        raise RuntimeError("服务端模型密钥加密主密钥未配置")
    key = base64.urlsafe_b64encode(hashlib.sha256(key_source.encode()).digest())
    return Fernet(key).decrypt(ciphertext).decode()


async def current_account(request: Request, session: AsyncSession) -> AccountRecord:
    token = request.cookies.get(get_settings().session_cookie_name)
    authorization = request.headers.get("authorization", "")
    if not token and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        raise HTTPException(401, "请先登录")
    record = await session.scalar(
        select(AccountSessionRecord).where(AccountSessionRecord.token_hash == token_hash(token))
    )
    if record is None:
        raise HTTPException(401, "登录已失效，请重新登录")
    from datetime import UTC, datetime

    if record.expires_at <= datetime.now(UTC):
        await session.delete(record)
        await session.commit()
        raise HTTPException(401, "登录已过期，请重新登录")
    account = await session.get(AccountRecord, record.account_id)
    if account is None:
        raise HTTPException(401, "账户不存在")
    return account


async def current_account_dependency(request: Request, session: SessionDep) -> AccountRecord:
    existing = getattr(request.state, "account", None)
    if existing is not None and getattr(existing, "id", None) is not None:
        return cast(AccountRecord, existing)
    account = await current_account(request, session)
    request.state.account_id = account.id
    request.state.account = account
    return account


async def require_project_owner(
    project_id: UUID,
    account: AccountRecord,
    session: AsyncSession,
) -> ProjectRecord:
    project = await session.get(ProjectRecord, project_id)
    if project is None or project.owner_id != account.id:
        raise HTTPException(404, "项目不存在")
    return project


async def require_project_owner_dependency(
    project_id: UUID,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
    session: SessionDep,
) -> ProjectRecord:
    return await require_project_owner(project_id, account, session)


async def _owned_project(project: ProjectRecord | None, account: AccountRecord) -> ProjectRecord:
    if project is None or project.owner_id != account.id:
        raise HTTPException(404, "资源不存在")
    return project


async def require_episode_owner(
    episode_id: UUID,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
    session: SessionDep,
) -> EpisodeRecord:
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise HTTPException(404, "资源不存在")
    project = await session.get(ProjectRecord, episode.project_id)
    await _owned_project(project, account)
    return episode


async def require_panel_owner(
    panel_id: UUID,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
    session: SessionDep,
) -> PanelRecord:
    panel = await session.get(PanelRecord, panel_id)
    if panel is None:
        raise HTTPException(404, "资源不存在")
    episode = await session.get(EpisodeRecord, panel.episode_id)
    if episode is None:
        raise HTTPException(404, "资源不存在")
    project = await session.get(ProjectRecord, episode.project_id)
    await _owned_project(project, account)
    return panel


async def require_task_owner(
    task_id: UUID,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
    session: SessionDep,
) -> GenerationTaskRecord:
    task = await session.get(GenerationTaskRecord, task_id)
    if task is None:
        raise HTTPException(404, "资源不存在")
    project = await session.get(ProjectRecord, task.project_id)
    await _owned_project(project, account)
    return task


async def require_asset_owner(
    asset_id: UUID,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
    session: SessionDep,
) -> UUID:
    export = await session.get(ExportRecord, asset_id)
    if export:
        project = await session.get(ProjectRecord, export.project_id)
        await _owned_project(project, account)
        return asset_id
    version = await session.scalar(
        select(ImageVersionRecord).where(ImageVersionRecord.asset_id == asset_id)
    )
    if version is not None:
        panel = await session.get(PanelRecord, version.panel_id)
        if panel is None:
            raise HTTPException(404, "资源不存在")
        episode = await session.get(EpisodeRecord, panel.episode_id)
        if episode is None:
            raise HTTPException(404, "资源不存在")
        project = await session.get(ProjectRecord, episode.project_id)
        await _owned_project(project, account)
        return asset_id
    character = await session.scalar(
        select(CharacterRecord).where(CharacterRecord.reference_asset_id == asset_id)
    )
    if character is not None:
        project = await session.get(ProjectRecord, character.project_id)
        await _owned_project(project, account)
        return asset_id
    scene = await session.scalar(
        select(SceneRecord).where(SceneRecord.reference_asset_id == asset_id)
    )
    if scene is None:
        raise HTTPException(404, "资源不存在")
    project = await session.get(ProjectRecord, scene.project_id)
    await _owned_project(project, account)
    return asset_id


async def require_character_owner(
    character_id: UUID,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
    session: SessionDep,
) -> CharacterRecord:
    character = await session.get(CharacterRecord, character_id)
    if character is None:
        raise HTTPException(404, "资源不存在")
    project = await session.get(ProjectRecord, character.project_id)
    await _owned_project(project, account)
    return character


async def require_scene_owner(
    scene_id: UUID,
    account: Annotated[AccountRecord, Depends(current_account_dependency)],
    session: SessionDep,
) -> SceneRecord:
    scene = await session.get(SceneRecord, scene_id)
    if scene is None:
        raise HTTPException(404, "资源不存在")
    project = await session.get(ProjectRecord, scene.project_id)
    await _owned_project(project, account)
    return scene


def check_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if not request.cookies.get(get_settings().session_cookie_name) and request.headers.get(
        "authorization", ""
    ).lower().startswith("bearer "):
        return
    cookie = request.cookies.get("manxu_csrf")
    header = request.headers.get("x-csrf-token")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise ApiError(
            "CSRF_INVALID",
            "请求校验失败，请刷新页面后重试。",
            status_code=403,
        )


async def validate_public_https_url(url: str) -> None:
    parsed = urlsplit(url)
    if not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422, "Base URL 必须是公网 HTTPS 地址")
    host = parsed.hostname.lower().rstrip(".")
    if get_settings().allow_private_model_base_urls:
        if parsed.scheme not in {"http", "https"}:
            raise HTTPException(422, "Base URL 必须是公网 HTTPS 地址")
        if host == "metadata.google.internal":
            raise HTTPException(422, "Base URL 不允许指向本地或元数据服务")
        return
    if parsed.scheme != "https":
        raise HTTPException(422, "Base URL 必须是公网 HTTPS 地址")
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".localhost"):
        raise HTTPException(422, "Base URL 不允许指向本地或元数据服务")
    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo, host, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except OSError as error:
        raise HTTPException(422, "Base URL 域名无法解析") from error
    ips = {ipaddress.ip_address(item[4][0]) for item in addresses}
    if not ips or any(not address.is_global for address in ips):
        raise HTTPException(422, "Base URL 不能解析到公网地址")


async def account_from_session(request: Request, session: AsyncSession) -> AccountRecord:
    check_csrf(request)
    return await current_account(request, session)
