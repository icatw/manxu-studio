"""Factory for the configured ObjectStore backend."""

from functools import lru_cache
from typing import cast

from app.core.config import get_settings
from app.providers.local_store import LocalObjectStore
from app.providers.protocols import ObjectStore
from app.providers.s3_store import S3ObjectStore


@lru_cache
def get_object_store() -> ObjectStore:
    settings = get_settings()
    if settings.object_store_backend == "s3":
        return cast(ObjectStore, S3ObjectStore())
    return cast(ObjectStore, LocalObjectStore())


def clear_object_store_cache() -> None:
    get_object_store.cache_clear()
