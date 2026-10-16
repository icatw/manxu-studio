import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_local_backend_default_does_not_require_s3() -> None:
    settings = Settings(
        _env_file=None,
        object_store_backend="local",
        generation_stale_running_seconds=100,
        generation_job_timeout_seconds=200,
        image_task_poll_interval_seconds=1,
        image_task_poll_max_attempts=10,
    )
    assert settings.object_store_backend == "local"


def test_s3_backend_requires_credentials() -> None:
    with pytest.raises(ValidationError, match="S3_BUCKET"):
        Settings(
            _env_file=None,
            object_store_backend="s3",
            s3_endpoint="https://cos.example.com",
            s3_bucket="",
            s3_access_key_id="",
            s3_secret_access_key="",
            generation_stale_running_seconds=100,
            generation_job_timeout_seconds=200,
            image_task_poll_interval_seconds=1,
            image_task_poll_max_attempts=10,
        )


def test_s3_backend_accepts_complete_config() -> None:
    settings = Settings(
        _env_file=None,
        object_store_backend="s3",
        s3_endpoint="https://cos.example.com",
        s3_bucket="bucket",
        s3_access_key_id="ak",
        s3_secret_access_key="sk",
        generation_stale_running_seconds=100,
        generation_job_timeout_seconds=200,
        image_task_poll_interval_seconds=1,
        image_task_poll_max_attempts=10,
    )
    assert settings.s3_region == "ap-guangzhou"
