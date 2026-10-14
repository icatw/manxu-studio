"""Seed an explicit demo project for local development only."""

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import AccountRecord, EpisodeRecord, ProjectRecord
from app.db.session import SessionFactory


async def seed(account_id: UUID) -> None:
    settings = get_settings()
    if settings.app_env != "development":
        raise RuntimeError("demo seed 只允许在 development 环境执行")
    async with SessionFactory() as session:
        account = await session.get(AccountRecord, account_id)
        if account is None:
            raise RuntimeError("指定账户不存在")
        existing = await session.scalar(
            select(ProjectRecord).where(
                ProjectRecord.owner_id == account_id,
                ProjectRecord.title == "本地演示项目",
            )
        )
        if existing is not None:
            print(existing.id)
            return
        project = ProjectRecord(
            owner_id=account_id,
            title="本地演示项目",
            synopsis="仅用于本地开发验证的演示故事。",
            genre="都市",
            art_style="电影感",
            aspect_ratio="portrait",
        )
        session.add(project)
        await session.flush()
        session.add(
            EpisodeRecord(
                project_id=project.id,
                title=project.title,
                synopsis=project.synopsis,
                panel_count=4,
            )
        )
        await session.commit()
        print(project.id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id", required=True, type=UUID)
    args = parser.parse_args()
    asyncio.run(seed(args.account_id))


if __name__ == "__main__":
    main()
