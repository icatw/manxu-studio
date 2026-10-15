from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AccountModelConfigRecord, GenerationTaskRecord


async def report_progress(session: AsyncSession, task: GenerationTaskRecord, progress: int) -> None:
    current = getattr(task, "progress", None) or 0
    task.progress = max(current, progress)
    task.updated_at = datetime.now(UTC)
    await session.commit()


async def require_text_model(session: AsyncSession, owner_id: UUID) -> AccountModelConfigRecord:
    config = await session.get(AccountModelConfigRecord, owner_id)
    if (
        config is None
        or not config.text_model
        or not config.text_base_url
        or not config.text_api_key_encrypted
    ):
        raise ValueError("请先在设置中保存并测试文本模型配置")
    return config


async def require_image_model(session: AsyncSession, owner_id: UUID) -> AccountModelConfigRecord:
    config = await session.get(AccountModelConfigRecord, owner_id)
    if config is None or not config.image_api_key_encrypted:
        raise ValueError("请先在模型设置中配置图像模型 API Key")
    return config
