"""Persist provider-call usage events for metering and cost transparency."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.core.correlation import (
    get_account_id,
    get_billing_source,
    get_generation_task_id,
    get_project_id,
    get_request_id,
)
from app.core.logging import api_logger
from app.db.models import UsageEventRecord
from app.db.session import SessionFactory

CallKind = Literal["text", "image"]
Outcome = Literal["success", "failed"]


async def record_usage_event(
    *,
    call_kind: CallKind,
    provider: str,
    model: str,
    outcome: Outcome,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    image_units: int | None = None,
    latency_ms: int | None = None,
    error_code: str | None = None,
    account_id: UUID | None = None,
    project_id: UUID | None = None,
    generation_task_id: UUID | None = None,
    request_id: str | None = None,
) -> UsageEventRecord | None:
    """Insert one usage row. Skips DB write when account_id is missing."""
    resolved_account = account_id or get_account_id()
    resolved_project = project_id if project_id is not None else get_project_id()
    resolved_task = (
        generation_task_id if generation_task_id is not None else get_generation_task_id()
    )
    resolved_request = request_id if request_id is not None else get_request_id()
    raw_billing = get_billing_source()
    billing_source = raw_billing if raw_billing in {"platform", "byok"} else "byok"
    billable = outcome == "success"

    log_extra = {
        "event": "provider_call_succeeded" if billable else "provider_call_failed",
        "request_id": resolved_request,
        "account_id": str(resolved_account) if resolved_account else None,
        "project_id": str(resolved_project) if resolved_project else None,
        "task_id": str(resolved_task) if resolved_task else None,
        "call_kind": call_kind,
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "image_units": image_units,
        "billable": billable,
        "billing_source": billing_source,
        "latency_ms": latency_ms,
        "outcome": outcome,
        "error_code": error_code,
    }
    if resolved_account is None:
        api_logger.info("provider_call_unattributed", extra=log_extra)
        return None

    record = UsageEventRecord(
        account_id=resolved_account,
        project_id=resolved_project,
        generation_task_id=resolved_task,
        request_id=resolved_request,
        call_kind=call_kind,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        image_units=image_units,
        outcome=outcome,
        billable=billable,
        billing_source=billing_source,
        latency_ms=latency_ms,
        error_code=error_code,
    )
    try:
        async with SessionFactory() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
    except Exception:
        api_logger.exception(
            "usage_event_persist_failed",
            extra={**log_extra, "event": "usage_event_persist_failed"},
        )
        return None

    api_logger.info(log_extra["event"], extra=log_extra)
    return record
