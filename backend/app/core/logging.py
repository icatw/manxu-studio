import json
import logging
import os
import re
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

BEARER_VALUE = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+")
SENSITIVE_VALUE = re.compile(
    r"(?i)(manxu_session|manxu_csrf|authorization|api[_-]?key|client[_-]?secret|"
    r"access[_-]?token|refresh[_-]?token|code|state)(\s*[=:]\s*|%3[dD])([^\s&,;]+)"
)


def _redact(value: str) -> str:
    return SENSITIVE_VALUE.sub(r"\1\2[REDACTED]", BEARER_VALUE.sub(r"\1[REDACTED]", value))


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": _redact(record.getMessage()),
        }
        for key in (
            "event",
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
            "error_code",
            "task_id",
            "account_id",
            "project_id",
            "job_id",
            "failure_id",
            "task_type",
            "call_kind",
            "model",
            "provider",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "image_units",
            "billable",
            "latency_ms",
            "outcome",
        ):
            value = getattr(record, key, None)
            if value is not None:
                event[key] = _redact(value) if isinstance(value, str) else value
        if record.exc_info:
            event["exception"] = _redact(self.formatException(record.exc_info))
        return json.dumps(event, ensure_ascii=True, separators=(",", ":"))


api_logger = logging.getLogger("manxu.api")


def configure_api_logging(*, app_env: str, log_dir: Path) -> None:
    api_logger.handlers.clear()
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False
    formatter = JsonLogFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    api_logger.addHandler(console_handler)

    if app_env != "development":
        return

    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_path = log_dir / "api.jsonl"
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    os.chmod(log_path, 0o600)
    file_handler.setFormatter(formatter)
    api_logger.addHandler(file_handler)
