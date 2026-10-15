from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db.models import AuthIdentityRecord
from app.services.auth_service import identity_is_verified


@pytest.mark.parametrize(
    ("provider", "email_verified_at", "expected"),
    [
        ("github", None, True),
        ("email", datetime(2026, 10, 15, tzinfo=UTC), True),
        ("email", None, False),
    ],
)
def test_identity_verification_uses_provider_semantics(
    provider: str, email_verified_at: datetime | None, expected: bool
) -> None:
    identity = AuthIdentityRecord(
        id=uuid4(),
        account_id=uuid4(),
        provider=provider,
        provider_subject="test-subject",
        email_verified_at=email_verified_at,
    )

    assert identity_is_verified(identity) is expected
