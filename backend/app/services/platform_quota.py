"""QUOTA-01: platform trial quota from usage_events (Asia/Shanghai calendar day)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.model_modes import normalize_model_mode
from app.db.models import AccountModelConfigRecord, GenerationTaskRecord, UsageEventRecord

_SHANGHAI = timezone(timedelta(hours=8))


def shanghai_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return [start, end) of the current Asia/Shanghai calendar day in UTC-aware datetimes."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    local = current.astimezone(_SHANGHAI)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


async def platform_usage_today(session: AsyncSession, account_id: UUID) -> tuple[int, int]:
    start, end = shanghai_day_bounds()
    text_count = await session.scalar(
        select(func.count())
        .select_from(UsageEventRecord)
        .where(
            UsageEventRecord.account_id == account_id,
            UsageEventRecord.billing_source == "platform",
            UsageEventRecord.billable.is_(True),
            UsageEventRecord.call_kind == "text",
            UsageEventRecord.created_at >= start,
            UsageEventRecord.created_at < end,
        )
    )
    image_sum = await session.scalar(
        select(func.coalesce(func.sum(UsageEventRecord.image_units), 0))
        .select_from(UsageEventRecord)
        .where(
            UsageEventRecord.account_id == account_id,
            UsageEventRecord.billing_source == "platform",
            UsageEventRecord.billable.is_(True),
            UsageEventRecord.call_kind == "image",
            UsageEventRecord.created_at >= start,
            UsageEventRecord.created_at < end,
        )
    )
    return int(text_count or 0), int(image_sum or 0)


async def quota_status_for_account(
    session: AsyncSession, account_id: UUID, *, model_mode: str | None = None
) -> dict[str, object]:
    settings = get_settings()
    mode = normalize_model_mode(model_mode)
    if mode != "platform" or not settings.platform_available:
        return {
            "applies": False,
            "text_remaining": None,
            "image_remaining": None,
            "exhausted": False,
            "message": None,
        }
    text_used, image_used = await platform_usage_today(session, account_id)
    text_limit = settings.platform_quota_text_per_day
    image_limit = settings.platform_quota_image_per_day
    text_remaining = None if text_limit <= 0 else max(0, text_limit - text_used)
    image_remaining = None if image_limit <= 0 else max(0, image_limit - image_used)
    exhausted = (text_remaining == 0) or (image_remaining == 0)
    message = "平台试用额度已用尽，请在设置中改用通义百炼或自备 Agnes。" if exhausted else None
    return {
        "applies": True,
        "text_remaining": text_remaining,
        "image_remaining": image_remaining,
        "exhausted": exhausted,
        "message": message,
    }


async def enforce_platform_quota_before_enqueue(session: AsyncSession, account_id: UUID) -> None:
    config = await session.get(AccountModelConfigRecord, account_id)
    mode = normalize_model_mode(getattr(config, "model_mode", None) if config else None)
    if mode != "platform":
        return
    settings = get_settings()
    if not settings.platform_available:
        raise HTTPException(status_code=409, detail="平台默认模型未启用，请改用自备模型")
    status = await quota_status_for_account(session, account_id, model_mode=mode)
    if status.get("exhausted"):
        raise HTTPException(
            status_code=402,
            detail=str(status.get("message") or "平台试用额度已用尽"),
        )
    active = list(
        (
            await session.scalars(
                select(GenerationTaskRecord).where(
                    GenerationTaskRecord.status.in_(("queued", "running"))
                )
            )
        ).all()
    )
    platform_running = sum(
        1
        for task in active
        if isinstance(task.request_data, dict)
        and task.request_data.get("billing_source") == "platform"
    )
    if platform_running >= settings.platform_max_running_tasks:
        raise HTTPException(
            status_code=429,
            detail="平台模型繁忙，请稍后再试或改用自备模型",
        )


def stamp_billing_source(request_data: dict[str, object], billing_source: str) -> dict[str, object]:
    merged = dict(request_data)
    merged["billing_source"] = billing_source
    return merged
