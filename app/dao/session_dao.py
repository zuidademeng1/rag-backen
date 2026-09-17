from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionDao:

    @classmethod
    async def get_by_id(cls, db: AsyncSession, session_id: str) -> Session | None:
        result = await db.execute(
            select(Session).where(Session.session_id == session_id, Session.del_flag == "0")
        )
        return result.scalars().first()

    @classmethod
    async def get_page(cls, db: AsyncSession, page_num: int, page_size: int, **filters) -> tuple[list[Session], int]:
        base = select(Session).where(Session.del_flag == "0")
        for key, value in filters.items():
            if value is not None and hasattr(Session, key):
                base = base.where(getattr(Session, key) == value)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        data_q = base.order_by(Session.create_time.desc()).offset(
            (page_num - 1) * page_size
        ).limit(page_size)
        items = list((await db.execute(data_q)).scalars().all())

        return items, total

    @classmethod
    async def add(cls, db: AsyncSession, session: Session) -> Session:
        db.add(session)
        await db.flush()
        return session

    @classmethod
    async def update(cls, db: AsyncSession, session: Session) -> Session:
        session = await db.merge(session)
        await db.flush()
        return session

    @classmethod
    async def delete(cls, db: AsyncSession, session_id: str) -> None:
        await db.execute(
            update(Session).where(Session.session_id == session_id).values(del_flag="2")
        )
        await db.flush()
