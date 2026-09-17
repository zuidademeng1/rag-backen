from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.session_dao import SessionDao
from app.dao.session_record_dao import SessionRecordDao
from app.models.session import Session
from app.models.session_record import SessionRecord
from app.schemas.session import (
    SessionCreateRequest,
    SessionUpdateRequest,
    SessionEntity,
    RecordAddRequest,
    RecordEntity,
)
from app.utils.auth_util import CurrentUser
from app.utils.common_util import generate_fast_id


class SessionService:

    @classmethod
    async def create_session(
        cls, db: AsyncSession, req: SessionCreateRequest, user: CurrentUser
    ) -> SessionEntity:
        session = Session(
            session_id=generate_fast_id(),
            title=req.title,
            user_id=str(user.user_id),
            dept_id=str(user.dept_id) if user.dept_id else None,
            create_by=user.user_name,
        )
        await SessionDao.add(db, session)
        return SessionEntity.model_validate(session)

    @classmethod
    async def get_page(
        cls, db: AsyncSession, page_num: int, page_size: int, user: CurrentUser
    ) -> tuple[list[dict], int]:
        items, total = await SessionDao.get_page(
            db, page_num=page_num, page_size=page_size, user_id=str(user.user_id)
        )
        rows = [
            SessionEntity.model_validate(item).model_dump(by_alias=True, mode="json")
            for item in items
        ]
        return rows, total

    @classmethod
    async def update_session(
        cls, db: AsyncSession, req: SessionUpdateRequest, user: CurrentUser
    ) -> SessionEntity | None:
        session = await SessionDao.get_by_id(db, req.session_id)
        if not session:
            return None
        if req.title is not None:
            session.title = req.title
        if req.status is not None:
            session.status = req.status
        session.update_by = user.user_name
        session.update_time = datetime.now()
        session = await SessionDao.update(db, session)
        return SessionEntity.model_validate(session)

    @classmethod
    async def delete_session(cls, db: AsyncSession, session_id: str) -> bool:
        session = await SessionDao.get_by_id(db, session_id)
        if not session:
            return False
        await SessionDao.delete(db, session_id)
        return True

    @classmethod
    async def add_record(
        cls, db: AsyncSession, req: RecordAddRequest, user: CurrentUser
    ) -> RecordEntity | None:
        session = await SessionDao.get_by_id(db, req.session_id)
        if not session:
            return None

        msg_index = await SessionRecordDao.get_next_msg_index(db, req.session_id)
        record = SessionRecord(
            record_id=generate_fast_id(),
            session_id=req.session_id,
            role=req.role,
            content=req.content,
            msg_index=msg_index,
            token_count=req.token_count,
            create_by=user.user_name,
        )
        await SessionRecordDao.add(db, record)
        return RecordEntity.model_validate(record)

    @classmethod
    async def get_records(
        cls, db: AsyncSession, session_id: str
    ) -> list[dict]:
        session = await SessionDao.get_by_id(db, session_id)
        if not session:
            return []
        items = await SessionRecordDao.get_list_by_session(db, session_id)
        return [
            RecordEntity.model_validate(item).model_dump(by_alias=True, mode="json")
            for item in items
        ]
