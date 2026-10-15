import asyncio
from pathlib import Path

from app.core.config import get_settings


class LocalObjectStore:
    """Filesystem-backed object store used until S3-compatible storage is wired."""

    def __init__(self, root: str | None = None) -> None:
        self._root = root

    def _directory(self) -> Path:
        return Path(self._root or get_settings().image_storage_dir).resolve()

    async def put_bytes(self, key: str, content: bytes) -> str:
        directory = await asyncio.to_thread(self._directory)
        await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)
        target = directory / Path(key).name
        await asyncio.to_thread(target.write_bytes, content)
        stem = Path(key).stem
        return f"/api/v1/assets/{stem}"

    def resolve_path(self, key: str) -> Path:
        return self._directory() / Path(key).name

    def find_asset_file(self, asset_id: str) -> Path | None:
        directory = self._directory()
        for suffix in (".png", ".jpg", ".webp"):
            candidate = directory / f"{asset_id}{suffix}"
            if candidate.is_file():
                return candidate
        return None
