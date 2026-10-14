from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.routes.workspace import download_export


class ExportSession:
    def __init__(self, record: SimpleNamespace) -> None:
        self.record = record

    async def get(self, model: type[object], asset_id: object) -> SimpleNamespace | None:
        return self.record if asset_id == self.record.id else None


@pytest.mark.asyncio
async def test_download_export_supports_utf8_filename() -> None:
    export_id = uuid4()
    record = SimpleNamespace(
        id=export_id,
        filename="雾港来信.png",
        content_type="image/png",
        content=b"png-content",
    )

    response = await download_export(export_id, ExportSession(record))  # type: ignore[arg-type]

    assert response.body == b"png-content"
    assert response.media_type == "image/png"
    assert (
        "filename*=UTF-8''%E9%9B%BE%E6%B8%AF%E6%9D%A5%E4%BF%A1.png"
        in response.headers["content-disposition"]
    )
