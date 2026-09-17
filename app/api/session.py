from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission import RequirePermission
from app.schemas.session import (
    SessionCreateRequest,
    SessionUpdateRequest,
    RecordAddRequest,
)
from app.services.session_service import SessionService
from app.utils.auth_util import AuthUtil, CurrentUser
from app.utils.response_util import ResponseUtil

router = APIRouter(prefix="/session", tags=["会话"])


@router.post("/add")
async def create_session(
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:session")),
):
    result = await SessionService.create_session(db, body, user)
    return ResponseUtil.success(data=result)


@router.get("/list")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:session")),
    page_num: int = 1,
    page_size: int = 10,
):
    rows, total = await SessionService.get_page(db, page_num, page_size, user)
    return ResponseUtil.paginate(rows=rows, total=total, page_num=page_num, page_size=page_size)


@router.put("/update")
async def update_session(
    body: SessionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:session")),
):
    result = await SessionService.update_session(db, body, user)
    if result is None:
        return ResponseUtil.error(msg="会话不存在")
    return ResponseUtil.success(data=result)


@router.delete("/delete")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:session")),
):
    ok = await SessionService.delete_session(db, session_id)
    if not ok:
        return ResponseUtil.error(msg="会话不存在")
    return ResponseUtil.success(msg="删除成功")


@router.post("/record/add")
async def add_record(
    body: RecordAddRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:session")),
):
    result = await SessionService.add_record(db, body, user)
    if result is None:
        return ResponseUtil.error(msg="会话不存在")
    return ResponseUtil.success(data=result)


@router.get("/record/list")
async def list_records(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:session")),
):
    rows = await SessionService.get_records(db, session_id)
    return ResponseUtil.success(data=rows)
