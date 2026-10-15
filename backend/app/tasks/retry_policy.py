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


def blocks_ordinary_retry(error: object) -> bool:
    code = task_error_code(error)
    return code in PROVIDER_PROTECTED_ERROR_CODES if code else False


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
        existing["remote_task_id"] = remote_task_id
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
        return
    if len(pending) > 1:
        raise ValueError("存在多个待绑定图像检查点，请指定 job_key")
    raise ValueError("任务没有可绑定的图像检查点；请确认远端任务后指定 job_key，或显式确认重新提交")
