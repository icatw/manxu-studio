"""S3-compatible object store (Tencent COS and peers)."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, cast

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings


class _S3Client(Protocol):
    def put_object(self, **kwargs: Any) -> Any: ...

    def get_object(self, **kwargs: Any) -> Any: ...

    def head_object(self, **kwargs: Any) -> Any: ...


_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
_ASSET_SUFFIXES = (".png", ".jpg", ".webp")


def _asset_url(key: str) -> str:
    name = key.rsplit("/", 1)[-1]
    for suffix in _ASSET_SUFFIXES:
        if name.endswith(suffix):
            return f"/api/v1/assets/{name[: -len(suffix)]}"
    stem = name.rsplit(".", 1)[0]
    return f"/api/v1/assets/{stem}"


def _content_type_for_key(key: str) -> str:
    lower = key.lower()
    for suffix, media_type in _MEDIA_TYPES.items():
        if lower.endswith(suffix):
            return media_type
    return "application/octet-stream"


class S3ObjectStore:
    """Put/get assets through an S3-compatible API (COS endpoint configurable)."""

    def __init__(self, settings: Settings | None = None, client: _S3Client | None = None) -> None:
        self._settings = settings
        self._client = client

    def _resolved_settings(self) -> Settings:
        return self._settings or get_settings()

    def _s3(self) -> _S3Client:
        if self._client is not None:
            return self._client
        settings = self._resolved_settings()
        addressing = settings.s3_addressing_style
        self._client = cast(
            _S3Client,
            boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint or None,
                region_name=settings.s3_region,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": addressing},
                ),
            ),
        )
        return self._client

    def _bucket(self) -> str:
        return self._resolved_settings().s3_bucket

    def put_bytes_sync(self, key: str, content: bytes) -> str:
        self._s3().put_object(
            Bucket=self._bucket(),
            Key=key,
            Body=content,
            ContentType=_content_type_for_key(key),
        )
        return _asset_url(key)

    def get_bytes_sync(self, key: str) -> bytes:
        response = self._s3().get_object(Bucket=self._bucket(), Key=key)
        body: Any = response["Body"]
        return bytes(body.read())

    def content_length(self, key: str) -> int | None:
        try:
            response = self._s3().head_object(Bucket=self._bucket(), Key=key)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        length = response.get("ContentLength")
        return int(length) if length is not None else None

    def _head_exists(self, key: str) -> bool:
        return self.content_length(key) is not None

    def find_asset_key(self, asset_id: str) -> str | None:
        for suffix in _ASSET_SUFFIXES:
            key = f"{asset_id}{suffix}"
            if self._head_exists(key):
                return key
        return None

    def read_asset_bytes(self, asset_id: str) -> bytes | None:
        key = self.find_asset_key(asset_id)
        if key is None:
            return None
        return self.get_bytes_sync(key)

    def open_asset(self, asset_id: str) -> tuple[bytes, str] | None:
        key = self.find_asset_key(asset_id)
        if key is None:
            return None
        return self.get_bytes_sync(key), _content_type_for_key(key)

    async def put_bytes(self, key: str, content: bytes) -> str:
        return await asyncio.to_thread(self.put_bytes_sync, key, content)

    async def get_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self.get_bytes_sync, key)

    async def open_asset_async(self, asset_id: str) -> tuple[bytes, str] | None:
        return await asyncio.to_thread(self.open_asset, asset_id)
