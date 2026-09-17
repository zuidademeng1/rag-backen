from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session_record import SessionRecord


class SessionRecordDao:

    @classmethod
    async def get_by_id(cls, db: AsyncSession, record_id: str) -> SessionRecord | None:
        result = await db.execute(
            select(SessionRecord).where(SessionRecord.record_id == record_id, SessionRecord.del_flag == "0")
        )
        return result.scalars().first()

    @classmethod
    async def get_list_by_session(cls, db: AsyncSession, session_id: str) -> list[SessionRecord]:
        result = await db.execute(
            select(SessionRecord)
            .where(SessionRecord.session_id == session_id, SessionRecord.del_flag == "0")
            .order_by(SessionRecord.msg_index.asc())
        )
        return list(result.scalars().all())

    @classmethod
    async def get_next_msg_index(cls, db: AsyncSession, session_id: str) -> int:
        result = await db.execute(
            select(func.coalesce(func.max(SessionRecord.msg_index), -1) + 1)
            .where(SessionRecord.session_id == session_id, SessionRecord.del_flag == "0")
        )
        return result.scalar() or 0

    @classmethod
    async def add(cls, db: AsyncSession, record: SessionRecord) -> SessionRecord:
        db.add(record)
        await db.flush()
        return record

    @classmethod
    async def delete_by_session(cls, db: AsyncSession, session_id: str) -> None:
        await db.execute(
            update(SessionRecord).where(SessionRecord.session_id == session_id).values(del_flag="2")
        )
        await db.flush()

    @classmethod
    async def count(cls, db: AsyncSession, **filters) -> int:
        query = select(SessionRecord).where(SessionRecord.del_flag == "0")
        for key, value in filters.items():
            if value is not None and hasattr(SessionRecord, key):
                query = query.where(getattr(SessionRecord, key) == value)
        result = await db.execute(query)
        return len(result.scalars().all())
