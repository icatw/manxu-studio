"""Request/task correlation context for logs and usage ledger."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID

_request_id: ContextVar[str | None] = ContextVar("manxu_request_id", default=None)
_account_id: ContextVar[UUID | None] = ContextVar("manxu_account_id", default=None)
_project_id: ContextVar[UUID | None] = ContextVar("manxu_project_id", default=None)
_generation_task_id: ContextVar[UUID | None] = ContextVar("manxu_generation_task_id", default=None)
_billing_source: ContextVar[str | None] = ContextVar("manxu_billing_source", default=None)


@dataclass(frozen=True, slots=True)
class CorrelationTokens:
    request_id: Token[str | None]
    account_id: Token[UUID | None]
    project_id: Token[UUID | None]
    generation_task_id: Token[UUID | None]
    billing_source: Token[str | None]


def get_request_id() -> str | None:
    return _request_id.get()


def get_account_id() -> UUID | None:
    return _account_id.get()


def get_project_id() -> UUID | None:
    return _project_id.get()


def get_generation_task_id() -> UUID | None:
    return _generation_task_id.get()


def get_billing_source() -> str | None:
    return _billing_source.get()


def set_request_id(value: str | None) -> Token[str | None]:
    return _request_id.set(value)


def set_account_id(value: UUID | None) -> Token[UUID | None]:
    return _account_id.set(value)


def set_project_id(value: UUID | None) -> Token[UUID | None]:
    return _project_id.set(value)


def set_generation_task_id(value: UUID | None) -> Token[UUID | None]:
    return _generation_task_id.set(value)


def set_billing_source(value: str | None) -> Token[str | None]:
    return _billing_source.set(value)


def bind_correlation(
    *,
    request_id: str | None = None,
    account_id: UUID | None = None,
    project_id: UUID | None = None,
    generation_task_id: UUID | None = None,
    billing_source: str | None = None,
) -> CorrelationTokens:
    return CorrelationTokens(
        request_id=set_request_id(request_id),
        account_id=set_account_id(account_id),
        project_id=set_project_id(project_id),
        generation_task_id=set_generation_task_id(generation_task_id),
        billing_source=set_billing_source(billing_source),
    )


def reset_correlation(tokens: CorrelationTokens) -> None:
    _request_id.reset(tokens.request_id)
    _account_id.reset(tokens.account_id)
    _project_id.reset(tokens.project_id)
    _generation_task_id.reset(tokens.generation_task_id)
    _billing_source.reset(tokens.billing_source)


def clear_correlation() -> None:
    _request_id.set(None)
    _account_id.set(None)
    _project_id.set(None)
    _generation_task_id.set(None)
    _billing_source.set(None)


def correlation_from_request_data(request_data: object) -> str | None:
    if not isinstance(request_data, dict):
        return None
    raw = request_data.get("_correlation")
    if not isinstance(raw, dict):
        return None
    value = raw.get("request_id")
    return value if isinstance(value, str) and value else None


def stamp_request_correlation(request_data: dict[str, object]) -> dict[str, object]:
    """Merge current request_id into request_data["_correlation"] (copy-safe)."""
    request_id = get_request_id()
    if not request_id:
        return request_data
    merged = dict(request_data)
    existing = merged.get("_correlation")
    correlation = dict(existing) if isinstance(existing, dict) else {}
    correlation["request_id"] = request_id
    merged["_correlation"] = correlation
    return merged
