import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import check_csrf, current_account, token_hash
from app.db.models import (
    AccountModelConfigRecord,
    AccountRecord,
    AccountRegistryRecord,
    AccountSessionRecord,
    OAuthStateRecord,
    ProjectRecord,
)
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["Authentication"])
SessionDep = Depends(get_session)


class AccountView(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    github_login: str
    display_name: str
    avatar_url: str | None


class AccountProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        display_name = value.strip()
        if not display_name:
            raise ValueError("昵称不能为空")
        return display_name


@router.get("/github/start", operation_id="startGitHubLogin", include_in_schema=True)
async def start_github_login(session: AsyncSession = SessionDep) -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        return RedirectResponse(
            f"{settings.frontend_base_url.rstrip('/')}/?auth_error=oauth_unconfigured",
            status_code=302,
        )
    state = secrets.token_urlsafe(32)
    session.add(
        OAuthStateRecord(
            state_hash=token_hash(state), expires_at=datetime.now(UTC) + timedelta(minutes=10)
        )
    )
    await session.execute(
        delete(OAuthStateRecord).where(OAuthStateRecord.expires_at <= datetime.now(UTC))
    )
    await session.commit()
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_callback_url,
            "scope": "read:user",
            "state": state,
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}", status_code=302)


@router.get("/github/callback", operation_id="completeGitHubLogin", include_in_schema=True)
async def github_callback(
    request: Request,
    response: Response,
    session: AsyncSession = SessionDep,
) -> RedirectResponse:
    settings = get_settings()
    frontend = settings.frontend_base_url.rstrip("/")
    query = request.query_params
    if query.get("error"):
        return RedirectResponse(f"{frontend}/?auth_error=denied", status_code=302)
    code, state = query.get("code"), query.get("state")
    if not code or not state:
        return RedirectResponse(f"{frontend}/?auth_error=invalid_callback", status_code=302)
    state_record = await session.scalar(
        select(OAuthStateRecord).where(OAuthStateRecord.state_hash == token_hash(state))
    )
    if state_record is None or state_record.expires_at <= datetime.now(UTC):
        return RedirectResponse(f"{frontend}/?auth_error=state", status_code=302)
    await session.delete(state_record)
    await session.commit()

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_callback_url,
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise ValueError("GitHub did not return an access token")
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            user_response.raise_for_status()
            github_user = user_response.json()
    except (httpx.HTTPError, ValueError):
        return RedirectResponse(f"{frontend}/?auth_error=github", status_code=302)

    registry = await session.scalar(
        select(AccountRegistryRecord).where(AccountRegistryRecord.id == 1).with_for_update()
    )
    if registry is None:
        return RedirectResponse(f"{frontend}/?auth_error=setup_required", status_code=302)
    github_id = int(github_user["id"])
    if registry.account_id is None:
        account = AccountRecord(
            id=uuid4(),
            github_id=github_id,
            github_login=str(github_user["login"]),
            display_name=str(github_user["login"]),
            avatar_url=github_user.get("avatar_url"),
        )
        session.add(account)
        await session.flush()
        registry.account_id = account.id
        await session.flush()
        await session.execute(
            update(ProjectRecord)
            .where(ProjectRecord.owner_id.is_(None))
            .values(owner_id=account.id)
        )
        session.add(
            AccountModelConfigRecord(
                account_id=account.id, image_base_url=settings.qwen_image_base_url
            )
        )
    else:
        existing_account = await session.get(AccountRecord, registry.account_id)
        if existing_account is None or existing_account.github_id != github_id:
            await session.rollback()
            return RedirectResponse(f"{frontend}/?auth_error=account_locked", status_code=302)
        existing_account.github_login = str(github_user["login"])
        if existing_account.display_name is None:
            existing_account.display_name = existing_account.github_login
        existing_account.avatar_url = github_user.get("avatar_url")
        account = existing_account

    raw_session = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    session.add(
        AccountSessionRecord(
            token_hash=token_hash(raw_session),
            account_id=account.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.session_ttl_days),
        )
    )
    await session.commit()
    redirect = RedirectResponse(frontend, status_code=302)
    redirect.set_cookie(
        settings.session_cookie_name,
        raw_session,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    redirect.set_cookie(
        "manxu_csrf",
        csrf_token,
        max_age=settings.session_ttl_days * 86400,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return redirect


@router.get("/me", operation_id="getCurrentAccount", response_model=AccountView)
async def get_current_account(
    request: Request,
    session: AsyncSession = SessionDep,
) -> AccountView:
    account = await current_account(request, session)
    if account.display_name is None:
        account.display_name = account.github_login
        await session.commit()
    return AccountView(
        id=str(account.id),
        github_login=account.github_login,
        display_name=account.display_name,
        avatar_url=account.avatar_url,
    )


@router.patch("/me", operation_id="updateCurrentAccount", response_model=AccountView)
async def update_current_account(
    body: AccountProfileUpdate,
    request: Request,
    session: AsyncSession = SessionDep,
) -> AccountView:
    check_csrf(request)
    account = await current_account(request, session)
    account.display_name = body.display_name
    await session.commit()
    return AccountView(
        id=str(account.id),
        github_login=account.github_login,
        display_name=body.display_name,
        avatar_url=account.avatar_url,
    )


@router.post("/logout", operation_id="logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = SessionDep,
) -> Response:
    check_csrf(request)
    await current_account(request, session)
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        record = await session.get(AccountSessionRecord, token_hash(token))
        if record:
            await session.delete(record)
            await session.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    response.delete_cookie("manxu_csrf", path="/")
    return response
