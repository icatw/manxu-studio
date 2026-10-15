"""Rules for ordinary retries vs provider-safe resume of generation tasks."""

from typing import Any

# Failures that may already own a remote provider job. Ordinary strip-and-retry
# would discard checkpoints and risk duplicate billing.
PROVIDER_PROTECTED_ERROR_CODES = frozenset(
    {
        "PROVIDER_SUBMIT_AMBIGUOUS",
        "RECOVERY_EXHAUSTED",
    }
)


def task_error_code(error: object) -> str | None:
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return str(code) if code is not None else None


def has_provider_resume_checkpoint(request_data: object) -> bool:
    if not isinstance(request_data, dict):
        return False
    raw_jobs = request_data.get("provider_jobs")
    if not isinstance(raw_jobs, dict):
        return False
    return any(
        isinstance(value, dict)
        and value.get("asset_id")
        and (value.get("remote_task_id") or value.get("submission_state") != "ready")
        for value in raw_jobs.values()
    )


def has_saved_remote_task_id(request_data: dict[str, Any]) -> bool:
    raw_jobs = request_data.get("provider_jobs")
    return isinstance(raw_jobs, dict) and any(
        isinstance(value, dict) and value.get("remote_task_id") for value in raw_jobs.values()
    )


def blocks_ordinary_retry(error: object, request_data: object = None) -> bool:
    code = task_error_code(error)
    return (
        code in PROVIDER_PROTECTED_ERROR_CODES if code else False
    ) or has_provider_resume_checkpoint(request_data)


def requires_resubmit_acknowledgment(request_data: dict[str, Any]) -> bool:
    raw_jobs = request_data.get("provider_jobs")
    if not isinstance(raw_jobs, dict):
        return False
    return any(
        isinstance(value, dict)
        and value.get("asset_id")
        and not value.get("remote_task_id")
        and value.get("submission_state") != "ready"
        for value in raw_jobs.values()
    )


def bind_remote_task_id(
    request_data: dict[str, Any],
    *,
    remote_task_id: str,
    job_key: str | None = None,
) -> None:
    """Attach a confirmed remote task id to provider image checkpoint(s)."""
    raw = request_data.get("provider_jobs")
    jobs: dict[str, Any]
    if isinstance(raw, dict):
        jobs = raw
    else:
        jobs = {}
        request_data["provider_jobs"] = jobs

    if job_key is not None:
        existing = jobs.get(job_key)
        if not isinstance(existing, dict) or not existing.get("asset_id"):
            raise ValueError("指定的图像检查点不存在")
        existing_remote_id = existing.get("remote_task_id")
        if existing_remote_id and existing_remote_id != remote_task_id:
            raise ValueError("指定的图像检查点已绑定其他远端任务")
        existing["remote_task_id"] = remote_task_id
        existing["submission_state"] = "submitted"
        return

    pending = [
        key
        for key, value in jobs.items()
        if isinstance(value, dict) and value.get("asset_id") and not value.get("remote_task_id")
    ]
    if len(pending) == 1:
        job = jobs[pending[0]]
        assert isinstance(job, dict)
        job["remote_task_id"] = remote_task_id
        job["submission_state"] = "submitted"
        return
    if len(pending) > 1:
        raise ValueError("存在多个待绑定图像检查点，请指定 job_key")
    raise ValueError("任务没有可绑定的图像检查点；请确认远端任务后指定 job_key，或显式确认重新提交")


def authorize_provider_resubmit(
    request_data: dict[str, Any], *, job_key: str | None = None, include_ready: bool = False
) -> None:
    """Reset ambiguous checkpoints only after the caller explicitly accepts resubmit."""
    raw_jobs = request_data.get("provider_jobs")
    jobs = raw_jobs if isinstance(raw_jobs, dict) else {}
    candidates = [
        key
        for key, value in jobs.items()
        if isinstance(value, dict)
        and value.get("asset_id")
        and not value.get("remote_task_id")
        and (include_ready or value.get("submission_state") != "ready")
    ]
    if job_key is not None:
        candidates = [key for key in candidates if key == job_key]
        if not candidates:
            raise ValueError("指定的待确认图像检查点不存在")
    elif len(candidates) > 1:
        raise ValueError("存在多个待确认图像检查点，请指定 job_key")
    elif not candidates:
        raise ValueError("任务没有待确认的图像检查点")

    checkpoint = jobs[candidates[0]]
    assert isinstance(checkpoint, dict)
    checkpoint["submission_state"] = "ready"
