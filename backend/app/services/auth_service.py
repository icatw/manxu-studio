"""Authentication application service."""

import asyncio
import hashlib
import hmac
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import consume_ephemeral_value, consume_rate_limit, set_ephemeral_value
from app.core.security import check_csrf, current_account, token_hash
from app.db.models import (
    AccountModelConfigRecord,
    AccountRecord,
    AccountSessionRecord,
    AuthIdentityRecord,
    EmailLoginChallengeRecord,
    OAuthStateRecord,
)

_development_email_pepper = secrets.token_urlsafe(48)


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


class EmailCodeRequest(BaseModel):
    email: EmailStr = Field(max_length=320)


class EmailVerifyRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    code: str = Field(min_length=6, max_length=6, pattern="^\\d{6}$")


class IdentityView(BaseModel):
    id: str
    provider: str
    email: str | None
    verified: bool


def identity_is_verified(identity: AuthIdentityRecord) -> bool:
    if identity.provider == "github":
        return True
    return identity.email_verified_at is not None


class CsrfTokenView(BaseModel):
    token: str


def normalize_email(value: str) -> str:
    return value.strip().lower()


def code_digest(email: str, code: str) -> str:
    settings = get_settings()
    pepper = settings.email_code_pepper
    if len(pepper) < 32 and settings.app_env == "development":
        pepper = _development_email_pepper
    if len(pepper) < 32:
        raise HTTPException(503, "服务端尚未配置邮箱验证码密钥")
    return hmac.new(pepper.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


async def send_email_code(email: str, code: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        if settings.app_env == "development":
            print(f"[DEV EMAIL] To: {email}; login code: {code}")
            return
        raise HTTPException(503, "服务端尚未配置邮件服务")

    def deliver() -> None:
        message = EmailMessage()
        message["Subject"] = "漫序 Studio 登录验证码"
        message["From"] = settings.smtp_from
        message["To"] = email
        message.set_content(f"你的漫序 Studio 登录验证码是 {code}，10 分钟内有效。")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)

    await asyncio.to_thread(deliver)


async def establish_session(
    account: AccountRecord, session: AsyncSession, response: Response
) -> Response:
    settings = get_settings()
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
    response.set_cookie(
        settings.session_cookie_name,
        raw_session,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "manxu_csrf",
        csrf_token,
        max_age=settings.session_ttl_days * 86400,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


async def get_csrf_token(
    request: Request, response: Response, session: AsyncSession
) -> CsrfTokenView:
    await current_account(request, session)
    token = secrets.token_urlsafe(32)
    settings = get_settings()
    response.set_cookie(
        "manxu_csrf",
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return CsrfTokenView(token=token)


async def request_email_code(body: EmailCodeRequest, session: AsyncSession) -> dict[str, str]:
    email = normalize_email(body.email)
    settings = get_settings()
    try:
        email_key = hashlib.sha256(email.encode()).hexdigest()
        allowed = await consume_rate_limit(f"auth:email:send:{email_key}", 3, 3600)
    except Exception as error:
        raise HTTPException(503, "验证码服务暂时不可用，请稍后重试") from error
    if not allowed:
        raise HTTPException(429, "验证码发送过于频繁，请稍后重试")
    now = datetime.now(UTC)
    latest = await session.scalar(
        select(EmailLoginChallengeRecord)
        .where(EmailLoginChallengeRecord.email_normalized == email)
        .order_by(EmailLoginChallengeRecord.created_at.desc())
        .limit(1)
    )
    if latest and (now - latest.last_sent_at).total_seconds() < settings.email_code_resend_seconds:
        raise HTTPException(429, "请稍后再获取验证码")
    code = f"{secrets.randbelow(1000000):06d}"
    digest = code_digest(email, code)
    challenge = EmailLoginChallengeRecord(
        email_normalized=email,
        code_digest=digest,
        expires_at=now + timedelta(seconds=settings.email_code_ttl_seconds),
        last_sent_at=now,
    )
    session.add(challenge)
    await session.commit()
    try:
        await set_ephemeral_value(
            f"email:code:{hashlib.sha256(email.encode()).hexdigest()}",
            digest,
            settings.email_code_ttl_seconds,
        )
        await send_email_code(email, code)
    except Exception as error:
        await session.delete(challenge)
        await session.commit()
        raise HTTPException(503, "验证码发送服务暂时不可用，请稍后重试") from error
    return {"message": "如果该邮箱可用，验证码已发送"}


async def verify_email_code(
    body: EmailVerifyRequest, response: Response, session: AsyncSession
) -> AccountView:
    email = normalize_email(body.email)
    challenge = await session.scalar(
        select(EmailLoginChallengeRecord)
        .where(
            EmailLoginChallengeRecord.email_normalized == email,
            EmailLoginChallengeRecord.consumed_at.is_(None),
        )
        .order_by(EmailLoginChallengeRecord.created_at.desc())
        .limit(1)
    )
    now = datetime.now(UTC)
    settings = get_settings()
    if challenge is None or challenge.expires_at <= now:
        raise HTTPException(401, "验证码无效或已过期")
    expected_digest = code_digest(email, body.code)
    if not hmac.compare_digest(challenge.code_digest, expected_digest):
        attempts = await session.scalar(
            update(EmailLoginChallengeRecord)
            .where(
                EmailLoginChallengeRecord.id == challenge.id,
                EmailLoginChallengeRecord.consumed_at.is_(None),
                EmailLoginChallengeRecord.expires_at > now,
                EmailLoginChallengeRecord.attempt_count < settings.email_code_max_attempts,
            )
            .values(attempt_count=EmailLoginChallengeRecord.attempt_count + 1)
            .returning(EmailLoginChallengeRecord.attempt_count)
        )
        await session.commit()
        message = "验证码错误，请重试" if attempts is not None else "验证码无效或已过期"
        raise HTTPException(401, message)
    if challenge.attempt_count >= settings.email_code_max_attempts:
        raise HTTPException(401, "验证码无效或已过期")
    try:
        code_consumed = await consume_ephemeral_value(
            f"email:code:{hashlib.sha256(email.encode()).hexdigest()}", expected_digest
        )
    except Exception as error:
        raise HTTPException(503, "验证码服务暂时不可用，请稍后重试") from error
    if not code_consumed:
        raise HTTPException(401, "验证码无效或已过期")
    claimed = await session.execute(
        update(EmailLoginChallengeRecord)
        .where(
            EmailLoginChallengeRecord.id == challenge.id,
            EmailLoginChallengeRecord.consumed_at.is_(None),
            EmailLoginChallengeRecord.expires_at > now,
            EmailLoginChallengeRecord.attempt_count < settings.email_code_max_attempts,
        )
        .values(consumed_at=now)
        .returning(EmailLoginChallengeRecord.id)
    )
    if claimed.scalar_one_or_none() is None:
        await session.rollback()
        raise HTTPException(401, "验证码无效或已过期")
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtext(f"email:{email}"))))
    identity = await session.scalar(
        select(AuthIdentityRecord).where(
            AuthIdentityRecord.provider == "email", AuthIdentityRecord.provider_subject == email
        )
    )
    if identity is None:
        account = AccountRecord(display_name=email.split("@", 1)[0])
        session.add(account)
        await session.flush()
        identity = AuthIdentityRecord(
            account_id=account.id,
            provider="email",
            provider_subject=email,
            email_original=body.email.strip(),
            email_normalized=email,
            email_verified_at=now,
        )
        session.add(identity)
        session.add(
            AccountModelConfigRecord(
                account_id=account.id, image_base_url=settings.qwen_image_base_url
            )
        )
    else:
        existing_account = await session.get(AccountRecord, identity.account_id)
        if existing_account is None:
            raise HTTPException(401, "账户不存在")
        account = existing_account
    await establish_session(account, session, response)
    return AccountView(
        id=str(account.id),
        github_login=account.github_login or "",
        display_name=account.display_name or email.split("@", 1)[0],
        avatar_url=account.avatar_url,
    )


async def start_github_login(session: AsyncSession) -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        return RedirectResponse(
            f"{settings.frontend_base_url.rstrip('/')}/?auth_error=oauth_unconfigured",
            status_code=302,
        )
    state = secrets.token_urlsafe(32)
    session.add(
        OAuthStateRecord(
            state_hash=token_hash(state),
            provider="github",
            intent="login",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
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
            "scope": "read:user user:email",
            "state": state,
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}", status_code=302)


async def github_callback(
    request: Request, response: Response, session: AsyncSession
) -> RedirectResponse:
    settings = get_settings()
    frontend = settings.frontend_base_url.rstrip("/")
    query = request.query_params
    if query.get("error"):
        return RedirectResponse(f"{frontend}/?auth_error=denied", status_code=302)
    code, state = (query.get("code"), query.get("state"))
    if not code or not state:
        return RedirectResponse(f"{frontend}/?auth_error=invalid_callback", status_code=302)
    consumed_state = await session.scalar(
        delete(OAuthStateRecord)
        .where(
            OAuthStateRecord.state_hash == token_hash(state),
            OAuthStateRecord.provider == "github",
            OAuthStateRecord.intent == "login",
            OAuthStateRecord.expires_at > datetime.now(UTC),
        )
        .returning(OAuthStateRecord.state_hash)
    )
    if consumed_state is None:
        return RedirectResponse(f"{frontend}/?auth_error=state", status_code=302)
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
    github_id = int(github_user["id"])
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtext(f"github:{github_id}"))))
    identity = await session.scalar(
        select(AuthIdentityRecord).where(
            AuthIdentityRecord.provider == "github",
            AuthIdentityRecord.provider_subject == str(github_id),
        )
    )
    if identity is None:
        account = AccountRecord(
            id=uuid4(),
            github_id=github_id,
            github_login=str(github_user["login"]),
            display_name=str(github_user["login"]),
            avatar_url=github_user.get("avatar_url"),
        )
        session.add(account)
        await session.flush()
        session.add(
            AuthIdentityRecord(
                account_id=account.id, provider="github", provider_subject=str(github_id)
            )
        )
        session.add(
            AccountModelConfigRecord(
                account_id=account.id, image_base_url=settings.qwen_image_base_url
            )
        )
    else:
        existing_account = await session.get(AccountRecord, identity.account_id)
        if existing_account is None:
            return RedirectResponse(f"{frontend}/?auth_error=account", status_code=302)
        existing_account.github_login = str(github_user["login"])
        if existing_account.display_name is None:
            existing_account.display_name = existing_account.github_login
        existing_account.avatar_url = github_user.get("avatar_url")
        account = existing_account
    redirect = RedirectResponse(frontend, status_code=302)
    await establish_session(account, session, redirect)
    return redirect


async def get_current_account(request: Request, session: AsyncSession) -> AccountView:
    account = await current_account(request, session)
    if account.display_name is None:
        account.display_name = account.github_login
        await session.commit()
    return AccountView(
        id=str(account.id),
        github_login=account.github_login or "",
        display_name=account.display_name or "账户",
        avatar_url=account.avatar_url,
    )


async def update_current_account(
    body: AccountProfileUpdate, request: Request, session: AsyncSession
) -> AccountView:
    check_csrf(request)
    account = await current_account(request, session)
    account.display_name = body.display_name
    await session.commit()
    return AccountView(
        id=str(account.id),
        github_login=account.github_login or "",
        display_name=body.display_name,
        avatar_url=account.avatar_url,
    )


async def list_auth_identities(request: Request, session: AsyncSession) -> list[IdentityView]:
    account = await current_account(request, session)
    identities = await session.scalars(
        select(AuthIdentityRecord).where(AuthIdentityRecord.account_id == account.id)
    )
    return [
        IdentityView(
            id=str(identity.id),
            provider=identity.provider,
            email=identity.email_original or identity.email_normalized,
            verified=identity_is_verified(identity),
        )
        for identity in identities
    ]


async def delete_auth_identity(
    identity_id: str, request: Request, response: Response, session: AsyncSession
) -> Response:
    check_csrf(request)
    account = await current_account(request, session)
    try:
        identity_uuid = UUID(identity_id)
    except ValueError as error:
        raise HTTPException(404, "登录身份不存在") from error
    identity = await session.get(AuthIdentityRecord, identity_uuid)
    if identity is None or identity.account_id != account.id:
        raise HTTPException(404, "登录身份不存在")
    await session.scalar(
        select(AccountRecord).where(AccountRecord.id == account.id).with_for_update()
    )
    count = await session.scalar(
        select(func.count(AuthIdentityRecord.id)).where(AuthIdentityRecord.account_id == account.id)
    )
    if count is not None and count <= 1:
        raise HTTPException(409, "账户至少需要保留一种登录方式")
    await session.delete(identity)
    await session.commit()
    response.status_code = 204
    return response


async def logout(request: Request, response: Response, session: AsyncSession) -> Response:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    authorization = request.headers.get("authorization", "")
    if not token and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token:
        record = await session.get(AccountSessionRecord, token_hash(token))
        if record:
            if record.expires_at > datetime.now(UTC) and request.cookies.get(
                settings.session_cookie_name
            ):
                check_csrf(request)
            await session.delete(record)
            await session.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie("manxu_csrf", path="/")
    response.status_code = 204
    return response
