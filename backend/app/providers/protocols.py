from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel


class TextProvider(Protocol):
    async def generate_structured[T: BaseModel](
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T: ...


class ImageProvider(Protocol):
    async def generate(
        self,
        *,
        api_key: str,
        model: str,
        prompt: str,
        asset_id: UUID,
        base_url: str | None = None,
        resume_task_id: str | None = None,
        on_submit_started: Callable[[], Awaitable[None]] | None = None,
        on_submit_rejected: Callable[[], Awaitable[None]] | None = None,
        on_submitted: Callable[[str], Awaitable[None]] | None = None,
    ) -> str: ...


class ObjectStore(Protocol):
    async def put_bytes(self, key: str, content: bytes) -> str: ...

    async def get_bytes(self, key: str) -> bytes: ...

    def find_asset_key(self, asset_id: str) -> str | None: ...

    def read_asset_bytes(self, asset_id: str) -> bytes | None: ...

    def open_asset(self, asset_id: str) -> tuple[bytes, str] | None: ...

    async def open_asset_async(self, asset_id: str) -> tuple[bytes, str] | None: ...
