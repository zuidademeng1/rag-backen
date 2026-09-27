from typing import Tuple
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.knowledge_base_dao import KnowledgeBaseDao
from app.dao.document_dao import DocumentDao
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreateRequest, KnowledgeBaseEntity
from app.utils.auth_util import CurrentUser
from app.utils.common_util import generate_fast_id


class KnowledgeBaseService:

    @classmethod
    async def create_knowledge_base(
            cls, db: AsyncSession, req: KnowledgeBaseCreateRequest, user: CurrentUser
    ) -> KnowledgeBaseEntity:
        if not req.kb_name or not req.kb_name.strip():
            raise HTTPException(status_code=400, detail="知识库名称不能为空")

        kb = KnowledgeBase(
            kb_id=generate_fast_id(),
            kb_name=req.kb_name,
            kb_desc=req.kb_desc,
            kb_icon=req.kb_icon,
            public_flag=req.public_flag,
            remark=req.remark,
            user_id=str(user.user_id),
            dept_id=str(user.dept_id) if user.dept_id else None,
            create_by=user.user_name,
            create_time=datetime.now(),
        )
        await KnowledgeBaseDao.add(db, kb)
        return KnowledgeBaseEntity(
            kb_id=kb.kb_id,
            kb_name=kb.kb_name,
            kb_desc=kb.kb_desc,
            kb_icon=kb.kb_icon,
            public_flag=kb.public_flag,
            remark=kb.remark,
            user_id=kb.user_id,
            dept_id=kb.dept_id,
            create_by=kb.create_by,
            create_time=kb.create_time,
        )

    @classmethod
    async def get_personal_page(
            cls, db: AsyncSession, page_num: int, page_size: int, user: CurrentUser
    ) -> Tuple[list[dict], int]:
        """获取当前用户的个人知识库分页列表"""
        items, total = await KnowledgeBaseDao.get_page(
            db, page_num=page_num, page_size=page_size,
            public_flag="0", user_id=str(user.user_id))
        rows = await cls._with_doc_count(db, items)
        return rows, total

    @classmethod
    async def get_kb_list_by_scope(
            cls, db: AsyncSession, scope: str, user: CurrentUser
    ) -> list[dict]:
        """按范围获取知识库列表（非分页，用于侧边栏）"""
        if scope == "personal":
            items = await KnowledgeBaseDao.get_list(
                db, public_flag="0", user_id=str(user.user_id))
        elif scope == "public":
            items = await KnowledgeBaseDao.get_list(db, public_flag="1")
        else:
            return []
        return [
            KnowledgeBaseEntity.model_validate(item).model_dump(by_alias=True, mode="json")
            for item in items
        ]

    @classmethod
    async def get_public_page(
            cls, db: AsyncSession, page_num: int, page_size: int, user: CurrentUser
    ) -> Tuple[list[dict], int]:
        """获取当前部门公共知识库分页列表"""
        items, total = await KnowledgeBaseDao.get_page(
            db, page_num=page_num, page_size=page_size,
            public_flag="1")
        rows = await cls._with_doc_count(db, items)
        return rows, total

    @classmethod
    async def _with_doc_count(cls, db: AsyncSession, items: list[KnowledgeBase]) -> list[dict]:
        """序列化知识库列表，并附上每个库的文档数量"""
        rows = []
        for item in items:
            row = KnowledgeBaseEntity.model_validate(item).model_dump(by_alias=True, mode="json")
            row["docCount"] = await DocumentDao.count(db, kb_id=item.kb_id)
            rows.append(row)
        return rows
