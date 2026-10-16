"""One-shot copy of local image volume files into S3-compatible object storage.

Does not delete local files (rollback = switch OBJECT_STORE_BACKEND back to local).
Requires Settings with object_store_backend=s3 (or pass an injected S3ObjectStore).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings
from app.providers.s3_store import S3ObjectStore

_ASSET_NAME = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"\.(png|jpg|webp)$",
    re.IGNORECASE,
)


class _MigrateTarget(Protocol):
    def content_length(self, key: str) -> int | None: ...

    def put_bytes_sync(self, key: str, content: bytes) -> str: ...

    def get_bytes_sync(self, key: str) -> bytes: ...


@dataclass(frozen=True)
class MigrateStats:
    scanned: int = 0
    uploaded: int = 0
    skipped: int = 0
    verified: int = 0
    failed: int = 0


def list_asset_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and _ASSET_NAME.match(path.name) is not None
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def migrate_file(
    path: Path,
    store: _MigrateTarget | None,
    *,
    dry_run: bool,
    skip_existing: bool,
    verify: bool,
) -> str:
    """Return action: uploaded|skipped|dry-run|verified."""
    key = path.name
    content = path.read_bytes()
    if dry_run:
        return "dry-run"
    if store is None:
        raise ValueError("store is required unless dry_run")
    if skip_existing:
        remote_len = store.content_length(key)
        if remote_len == len(content):
            if verify:
                remote = store.get_bytes_sync(key)
                if remote != content:
                    raise ValueError(f"size matched but bytes differ for {key}")
            return "skipped"
    store.put_bytes_sync(key, content)
    if verify:
        remote = store.get_bytes_sync(key)
        if remote != content:
            raise ValueError(f"verify failed for {key} (sha local={_sha256(content)})")
        return "verified"
    return "uploaded"


def migrate_directory(
    root: Path,
    store: _MigrateTarget | None,
    *,
    dry_run: bool = False,
    skip_existing: bool = True,
    verify: bool = True,
    paths: Iterable[Path] | None = None,
) -> MigrateStats:
    if not dry_run and store is None:
        raise ValueError("store is required unless dry_run")
    files = list(paths) if paths is not None else list_asset_files(root)
    uploaded = skipped = verified = failed = 0
    for path in files:
        try:
            action = migrate_file(
                path,
                store,
                dry_run=dry_run,
                skip_existing=skip_existing,
                verify=verify,
            )
        except (OSError, ClientError, ValueError) as error:
            failed += 1
            print(f"FAIL {path.name}: {error}", file=sys.stderr)
            continue
        if action == "skipped":
            skipped += 1
            print(f"SKIP {path.name}")
        elif action == "dry-run":
            print(f"DRY  {path.name} ({path.stat().st_size} bytes)")
        elif action == "verified":
            uploaded += 1
            verified += 1
            print(f"OK   {path.name} (verified)")
        else:
            uploaded += 1
            print(f"OK   {path.name}")
    return MigrateStats(
        scanned=len(files),
        uploaded=uploaded,
        skipped=skipped,
        verified=verified,
        failed=failed,
    )


def build_store(settings: Settings) -> S3ObjectStore:
    if settings.object_store_backend != "s3":
        raise RuntimeError("migrate_images_to_s3 需要 OBJECT_STORE_BACKEND=s3 与完整 S3_* 配置")
    return S3ObjectStore(settings=settings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy local IMAGE_STORAGE_DIR asset files into S3/COS."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Local image directory (default: Settings.image_storage_dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would upload; do not write to the bucket",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-upload even when remote ContentLength matches",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip byte comparison after upload",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    root = (args.source or Path(settings.image_storage_dir)).resolve()
    if not root.is_dir():
        print(f"source directory missing: {root}", file=sys.stderr)
        return 2

    # dry-run only lists local files; S3 credentials required for real upload.
    store = None if args.dry_run else build_store(settings)
    stats = migrate_directory(
        root,
        store,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip_existing,
        verify=not args.no_verify,
    )
    print(
        "done:"
        f" scanned={stats.scanned}"
        f" uploaded={stats.uploaded}"
        f" skipped={stats.skipped}"
        f" verified={stats.verified}"
        f" failed={stats.failed}"
    )
    return 1 if stats.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
