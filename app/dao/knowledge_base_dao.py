from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

# 数据库层就必须用它
from app.models.knowledge_base import KnowledgeBase


class KnowledgeBaseDao:
    """知识库表数据库操作层"""

    @classmethod
    async def get_by_id(cls, db: AsyncSession, kb_id: str) -> KnowledgeBase | None:
        """
        根据主键获取知识库
        :param db: orm对象
        :param kb_id: 知识库主键
        :return: 知识库对象
        """
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id, KnowledgeBase.del_flag == '0')
        )
        return result.scalars().first()

    @classmethod
    async def get_list(cls, db: AsyncSession, **filters) -> list[KnowledgeBase]:
        """
        获取知识库列表（支持按字段过滤）
        :param db: orm对象
        :param filters: 过滤条件，如 dept_id=1
        :return: 知识库列表
        """
        query = select(KnowledgeBase).where(KnowledgeBase.del_flag == '0')
        for key, value in filters.items():
            if value is not None and hasattr(KnowledgeBase, key):
                query = query.where(getattr(KnowledgeBase, key) == value)
        query = query.order_by(KnowledgeBase.create_time.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def get_page(cls, db: AsyncSession, page_num: int, page_size: int, **filters) -> tuple[list[KnowledgeBase], int]:
        """分页查询（支持字段过滤）"""
        base = select(KnowledgeBase).where(KnowledgeBase.del_flag == '0')
        for key, value in filters.items():
            if value is not None and hasattr(KnowledgeBase, key):
                base = base.where(getattr(KnowledgeBase, key) == value)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        data_q = base.order_by(KnowledgeBase.create_time.desc()).offset(
            (page_num - 1) * page_size
        ).limit(page_size)
        items = list((await db.execute(data_q)).scalars().all())

        return items, total

    @classmethod
    async def add(cls, db: AsyncSession, kb: KnowledgeBase) -> KnowledgeBase:
        """
        新增知识库
        :param db: orm对象
        :param kb: 知识库对象
        :return: 知识库对象
        """
        db.add(kb)
        await db.flush()
        return kb

    @classmethod
    async def update(cls, db: AsyncSession, kb: KnowledgeBase) -> KnowledgeBase:
        """
        更新知识库
        :param db: orm对象
        :param kb: 知识库对象（需包含 kb_id）
        :return: 知识库对象
        """
        await db.merge(kb)
        await db.flush()
        return kb

    @classmethod
    async def delete(cls, db: AsyncSession, kb_id: str) -> None:
        """
        软删除知识库（标记 del_flag = '2'）
        :param db: orm对象
        :param kb_id: 知识库主键
        """
        await db.execute(
            update(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id).values(del_flag='2')
        )
        await db.flush()

    @classmethod
    async def batch_delete(cls, db: AsyncSession, kb_ids: list[str]) -> None:
        """
        批量软删除知识库
        :param db: orm对象
        :param kb_ids: 知识库主键列表
        """
        await db.execute(
            update(KnowledgeBase).where(KnowledgeBase.kb_id.in_(kb_ids)).values(del_flag='2')
        )
        await db.flush()

    @classmethod
    async def delete_hard(cls, db: AsyncSession, kb_id: str) -> None:
        """
        硬删除知识库（从数据库彻底删除）
        :param db: orm对象
        :param kb_id: 知识库主键
        """
        kb = await cls.get_by_id(db, kb_id)
        if kb:
            await db.delete(kb)
            await db.flush()

    @classmethod
    async def count(cls, db: AsyncSession, **filters) -> int:
        """
        统计知识库数量
        :param db: orm对象
        :param filters: 过滤条件
        :return: 数量
        """
        query = select(KnowledgeBase).where(KnowledgeBase.del_flag == '0')
        for key, value in filters.items():
            if value is not None and hasattr(KnowledgeBase, key):
                query = query.where(getattr(KnowledgeBase, key) == value)
        result = await db.execute(query)
        return len(result.scalars().all())
