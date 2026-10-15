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
        on_submitted: object | None = None,
    ) -> str: ...


class ObjectStore(Protocol):
    async def put_bytes(self, key: str, content: bytes) -> str: ...

    def resolve_path(self, key: str) -> str: ...
