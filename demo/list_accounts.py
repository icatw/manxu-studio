import asyncio

from sqlalchemy import func, select

from app.db.models import AccountRecord, EpisodeRecord, ProjectRecord
from app.db.session import SessionFactory


async def main() -> None:
    async with SessionFactory() as s:
        rows = await s.execute(
            select(
                AccountRecord.id,
                AccountRecord.display_name,
                AccountRecord.github_login,
                func.count(ProjectRecord.id),
            )
            .outerjoin(ProjectRecord, ProjectRecord.owner_id == AccountRecord.id)
            .group_by(AccountRecord.id)
            .order_by(func.count(ProjectRecord.id).desc())
        )
        for r in rows.all():
            print(f"account={r[0]} name={r[1]!r} github={r[2]!r} projects={r[3]}")
        richest = await s.execute(
            select(ProjectRecord.id, ProjectRecord.title, ProjectRecord.owner_id)
            .order_by(ProjectRecord.updated_at.desc())
            .limit(10)
        )
        print("---projects---")
        for p in richest.all():
            eps = await s.scalar(
                select(func.count()).select_from(EpisodeRecord).where(EpisodeRecord.project_id == p[0])
            )
            print(f"  {p[0]} {p[1]!r} owner={p[2]} episodes={eps}")


if __name__ == "__main__":
    asyncio.run(main())
