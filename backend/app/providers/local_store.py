import asyncio
from pathlib import Path

from app.core.config import get_settings

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
}


class LocalObjectStore:
    """Filesystem-backed object store used for local development and CI."""

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

    def find_asset_key(self, asset_id: str) -> str | None:
        path = self.find_asset_file(asset_id)
        return path.name if path is not None else None

    def read_asset_bytes(self, asset_id: str) -> bytes | None:
        path = self.find_asset_file(asset_id)
        return path.read_bytes() if path is not None else None

    def open_asset(self, asset_id: str) -> tuple[bytes, str] | None:
        path = self.find_asset_file(asset_id)
        if path is None:
            return None
        media_type = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return path.read_bytes(), media_type

    async def get_bytes(self, key: str) -> bytes:
        path = self.resolve_path(key)
        return await asyncio.to_thread(path.read_bytes)

    async def open_asset_async(self, asset_id: str) -> tuple[bytes, str] | None:
        return await asyncio.to_thread(self.open_asset, asset_id)
