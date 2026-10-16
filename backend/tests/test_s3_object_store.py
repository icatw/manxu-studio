from types import SimpleNamespace
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.providers.s3_store import S3ObjectStore


class FakeBody:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> dict[str, str]:
        self.put_calls.append(kwargs)
        key = str(kwargs["Key"])
        body = kwargs["Body"]
        assert isinstance(body, (bytes, bytearray))
        self.objects[key] = bytes(body)
        return {}

    def get_object(self, **kwargs: object) -> dict[str, object]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
                "GetObject",
            )
        return {"Body": FakeBody(self.objects[key])}

    def head_object(self, **kwargs: object) -> dict[str, str]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "missing"}},
                "HeadObject",
            )
        return {}


@pytest.mark.asyncio
async def test_s3_put_and_open_asset_roundtrip() -> None:
    client = FakeS3Client()
    settings = SimpleNamespace(
        s3_bucket="manxu-test",
        s3_endpoint="https://cos.example.com",
        s3_region="ap-guangzhou",
        s3_access_key_id="ak",
        s3_secret_access_key="sk",
        s3_addressing_style="virtual",
    )
    store = S3ObjectStore(settings=settings, client=client)  # type: ignore[arg-type]
    asset_id = uuid4()
    content = b"\x89PNG-fake"

    url = await store.put_bytes(f"{asset_id}.png", content)
    assert url == f"/api/v1/assets/{asset_id}"
    assert client.put_calls[0]["ContentType"] == "image/png"
    assert client.put_calls[0]["Bucket"] == "manxu-test"

    opened = store.open_asset(str(asset_id))
    assert opened == (content, "image/png")
    assert store.find_asset_key(str(asset_id)) == f"{asset_id}.png"
    assert store.read_asset_bytes(str(asset_id)) == content


def test_s3_open_asset_missing_returns_none() -> None:
    client = FakeS3Client()
    settings = SimpleNamespace(
        s3_bucket="manxu-test",
        s3_endpoint="https://cos.example.com",
        s3_region="ap-guangzhou",
        s3_access_key_id="ak",
        s3_secret_access_key="sk",
        s3_addressing_style="path",
    )
    store = S3ObjectStore(settings=settings, client=client)  # type: ignore[arg-type]
    assert store.open_asset(str(uuid4())) is None
