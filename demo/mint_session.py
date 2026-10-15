"""Mint a development session cookie for demo recording (run inside api container)."""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import token_hash
from app.db.models import AccountRecord, AccountSessionRecord, AuthIdentityRecord
from app.db.session import SessionFactory


async def main() -> None:
    settings = get_settings()
    email = "demo-recorder@manxu.dev"
    async with SessionFactory() as session:
        identity = await session.scalar(
            select(AuthIdentityRecord).where(
                AuthIdentityRecord.provider == "email",
                AuthIdentityRecord.provider_subject == email,
            )
        )
        if identity is not None:
            account = await session.get(AccountRecord, identity.account_id)
            assert account is not None
        else:
            account = AccountRecord(display_name="演示录屏")
            session.add(account)
            await session.flush()
            session.add(
                AuthIdentityRecord(
                    account_id=account.id,
                    provider="email",
                    provider_subject=email,
                    email_original=email,
                    email_normalized=email,
                    email_verified_at=datetime.now(UTC),
                )
            )
        raw = secrets.token_urlsafe(48)
        session.add(
            AccountSessionRecord(
                token_hash=token_hash(raw),
                account_id=account.id,
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )
        await session.commit()
        print(settings.session_cookie_name)
        print(raw)
        print(str(account.id))


if __name__ == "__main__":
    asyncio.run(main())
