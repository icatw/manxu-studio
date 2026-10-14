import asyncio
import base64
import hashlib
import hmac
import ipaddress
import socket
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_responses import ApiError
from app.core.config import get_settings
from app.db.models import AccountRecord, AccountSessionRecord


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def encrypt_secret(secret: str) -> bytes:
    key_source = get_settings().model_encryption_key
    if len(key_source) < 32:
        raise HTTPException(503, "服务端尚未配置模型密钥加密主密钥")
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
    if not token:
        raise HTTPException(401, "请先使用 GitHub 登录")
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


def check_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
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
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422, "Base URL 必须是公网 HTTPS 地址")
    host = parsed.hostname.lower().rstrip(".")
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
