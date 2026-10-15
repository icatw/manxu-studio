"""Helpers for durable stage / provider checkpoints on generation tasks."""

from copy import deepcopy
from typing import Any

CHECKPOINT_KEYS = ("provider_jobs", "pipeline_stages")


def strip_resumable_checkpoints(request_data: dict[str, Any]) -> dict[str, Any]:
    """Copy request payload without provider/pipeline resume state for explicit retries."""
    cleaned = deepcopy(request_data)
    for key in CHECKPOINT_KEYS:
        cleaned.pop(key, None)
    return cleaned
