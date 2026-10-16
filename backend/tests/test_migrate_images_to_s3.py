from pathlib import Path
from uuid import uuid4

from botocore.exceptions import ClientError

from app.cli.migrate_images_to_s3 import list_asset_files, migrate_directory
from app.providers.s3_store import S3ObjectStore


class FakeBody:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def read(self) -> bytes:
        return self._content


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs: object) -> dict[str, str]:
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

    def head_object(self, **kwargs: object) -> dict[str, int]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "missing"}},
                "HeadObject",
            )
        return {"ContentLength": len(self.objects[key])}


def _store() -> S3ObjectStore:
    from types import SimpleNamespace

    settings = SimpleNamespace(
        s3_bucket="manxu-test",
        s3_endpoint="https://cos.example.com",
        s3_region="ap-guangzhou",
        s3_access_key_id="ak",
        s3_secret_access_key="sk",
        s3_addressing_style="virtual",
    )
    return S3ObjectStore(settings=settings, client=FakeS3Client())  # type: ignore[arg-type]


def test_list_asset_files_filters_names(tmp_path: Path) -> None:
    good = tmp_path / f"{uuid4()}.png"
    good.write_bytes(b"png")
    (tmp_path / "readme.txt").write_text("nope")
    (tmp_path / "not-a-uuid.jpg").write_bytes(b"x")
    assert list_asset_files(tmp_path) == [good]


def test_migrate_uploads_verifies_and_skips(tmp_path: Path) -> None:
    store = _store()
    asset = uuid4()
    path = tmp_path / f"{asset}.png"
    path.write_bytes(b"\x89PNG-data")

    first = migrate_directory(tmp_path, store, dry_run=False, skip_existing=True, verify=True)
    assert first.uploaded == 1
    assert first.verified == 1
    assert first.failed == 0

    second = migrate_directory(tmp_path, store, dry_run=False, skip_existing=True, verify=True)
    assert second.skipped == 1
    assert second.uploaded == 0


def test_migrate_dry_run_does_not_write(tmp_path: Path) -> None:
    store = _store()
    path = tmp_path / f"{uuid4()}.webp"
    path.write_bytes(b"webp-bytes")
    stats = migrate_directory(tmp_path, store, dry_run=True, skip_existing=True, verify=True)
    assert stats.scanned == 1
    assert stats.uploaded == 0
    assert store.content_length(path.name) is None
