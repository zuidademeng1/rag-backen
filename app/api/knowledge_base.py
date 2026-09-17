from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission import RequirePermission
from app.dao.document_dao import DocumentDao
from app.dao.knowledge_base_dao import KnowledgeBaseDao
from app.schemas.knowledge_base import KnowledgeBaseCreateRequest, KnowledgeBaseEntity
from app.services.knowledge_base_service import KnowledgeBaseService
from app.utils.auth_util import AuthUtil, CurrentUser
from app.utils.response_util import ResponseUtil

router = APIRouter(prefix="/knowledgeBase", tags=["知识库"])

# 创建知识库
@router.post("/add")
async def create_knowledge_base(
    body: KnowledgeBaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:kb:add")),
):
    result = await KnowledgeBaseService.create_knowledge_base(db, body, user)
    return ResponseUtil.success(data=result)

# 删除个人知识库
@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:kb:delete")),
):
    kb = await KnowledgeBaseDao.get_by_id(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if kb.public_flag == "1":
        raise HTTPException(status_code=403, detail="不能删除公共知识库")
    if str(kb.user_id) != str(user.user_id):
        raise HTTPException(status_code=403, detail="只能删除自己的知识库")

    doc_count = await DocumentDao.count(db, kb_id=kb_id)
    warn = None
    if doc_count > 0:
        warn = f"知识库中有 {doc_count} 个文档,请勿删除"

    await KnowledgeBaseDao.delete(db, kb_id)
    return ResponseUtil.success(msg=warn or "删除成功")


# 批量删除个人知识库
@router.post("/batch-delete")
async def batch_delete_knowledge_base(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:kb:delete")),
):
    kb_ids: list[str] = body.get("kb_ids", [])
    if not kb_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的知识库")

    # 校验所有知识库：只能删除自己的个人知识库
    clean_ids: list[str] = []
    warn_names: list[str] = []
    for kb_id in kb_ids:
        kb = await KnowledgeBaseDao.get_by_id(db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库 {kb_id} 不存在")
        if kb.public_flag == "1":
            raise HTTPException(status_code=403, detail=f"知识库 {kb.kb_name} 是公共知识库，不能删除")
        if str(kb.user_id) != str(user.user_id):
            raise HTTPException(status_code=403, detail=f"知识库 {kb.kb_name} 不属于当前用户")

        doc_count = await DocumentDao.count(db, kb_id=kb_id)
        if doc_count > 0:
            warn_names.append(kb.kb_name)
        else:
            clean_ids.append(kb_id)

    msg_parts = []
    if clean_ids:
        await KnowledgeBaseDao.batch_delete(db, clean_ids)
        msg_parts.append(f"成功删除 {len(clean_ids)} 个知识库")
    if warn_names:
        msg_parts.append(f"{'、'.join(warn_names)} 含有文档，不能删除")

    return ResponseUtil.success(msg="；".join(msg_parts))


# 获取个人知识库列表（分页）
@router.get("/personal")
async def get_personal_list(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:kb:list")),
    page_num: int = 1,
    page_size: int = 10,
):
    rows, total = await KnowledgeBaseService.get_personal_page(db, page_num, page_size, user)
    return ResponseUtil.paginate(rows=rows, total=total, page_num=page_num, page_size=page_size)

# 获取知识库列表（按范围，非分页，用于侧边栏）
@router.get("/scope")
async def get_kb_by_scope(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:kb:list")),
    scope: str = "personal",
):
    rows = await KnowledgeBaseService.get_kb_list_by_scope(db, scope, user)
    return ResponseUtil.success(data=rows)


# 获取公共知识库列表（分页）
@router.get("/public")
async def get_public_list(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:kb:list")),
    page_num: int = 1,
    page_size: int = 10,
):
    rows, total = await KnowledgeBaseService.get_public_page(db, page_num, page_size, user)
    return ResponseUtil.paginate(rows=rows, total=total, page_num=page_num, page_size=page_size)