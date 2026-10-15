import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from app.db.models import EpisodeRecord
from app.db.session import SessionFactory


async def main(project_id: UUID) -> None:
    async with SessionFactory() as s:
        episodes = (
            await s.scalars(
                select(EpisodeRecord)
                .where(EpisodeRecord.project_id == project_id)
                .order_by(EpisodeRecord.created_at.asc())
            )
        ).all()
        for ep in episodes:
            print(f"{ep.id}\t{ep.title}\torder={getattr(ep, 'sort_order', None)}")


if __name__ == "__main__":
    asyncio.run(main(UUID(sys.argv[1])))
