"""Mint session for an existing account id. Run inside api container."""

from __future__ import annotations

import asyncio
import secrets
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import get_settings
from app.core.security import token_hash
from app.db.models import AccountRecord, AccountSessionRecord
from app.db.session import SessionFactory


async def main(account_id: UUID) -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        account = await session.get(AccountRecord, account_id)
        if account is None:
            raise SystemExit(f"account not found: {account_id}")
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
        print(account.display_name or "")


if __name__ == "__main__":
    asyncio.run(main(UUID(sys.argv[1])))
