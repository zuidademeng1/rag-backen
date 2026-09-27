from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentDao:
    """文档表数据库操作层"""

    @classmethod
    async def get_by_id(cls, db: AsyncSession, doc_id: str) -> Document | None:
        """
        根据主键获取文档
        :param db: orm对象
        :param doc_id: 文档主键
        :return: 文档对象
        """
        result = await db.execute(
            select(Document).where(Document.doc_id == doc_id, Document.del_flag == '0')
        )
        return result.scalars().first()

    @classmethod
    async def get_list(cls, db: AsyncSession, **filters) -> list[Document]:
        """
        获取文档列表（支持按字段过滤）
        :param db: orm对象
        :param filters: 过滤条件，如 kb_id=1, dept_id=2
        :return: 文档列表
        """
        query = select(Document).where(Document.del_flag == '0')
        #hasattr(对象, "属性名")  → 这个对象有这个属性，返回 True ；没有，返回   False
        for key, value in filters.items():
            #hasattr(Document, key)和getattr(Document, key)配合使用，前者先判断有没有这个属性，后者再取值判断是否等于value
            #hasattr(Document, key)防止传错字段名导致报错。比如拼错kb_id拼成kbbid
            if value is not None and hasattr(Document, key):
                query = query.where(getattr(Document, key) == value)
        query = query.order_by(Document.upload_time.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def get_page(cls, db: AsyncSession, page_num: int, page_size: int, keyword: str | None = None, **filters) -> tuple[list[Document], int]:
        """分页查询文档（支持字段过滤 + 文件名模糊搜索）"""
        from sqlalchemy import select, func
        base = select(Document).where(Document.del_flag == '0')
        if keyword:
            base = base.where(Document.file_name.ilike(f'%{keyword}%'))
        for key, value in filters.items():
            if value is not None and hasattr(Document, key):
                base = base.where(getattr(Document, key) == value)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        data_q = base.order_by(Document.upload_time.desc()).offset(
            (page_num - 1) * page_size
        ).limit(page_size)
        items = list((await db.execute(data_q)).scalars().all())
        return items, total

    @classmethod
    async def get_public_page(cls, db: AsyncSession, page_num: int, page_size: int,
                              keyword: str | None = None, kb_id: str | None = None) -> tuple[list[Document], int]:
        """分页查询公共知识库文档（全校可见，不分部门）"""
        from sqlalchemy import select, func
        from app.models.knowledge_base import KnowledgeBase

        base = (
            select(Document)
            .join(KnowledgeBase, Document.kb_id == KnowledgeBase.kb_id)
            .where(
                Document.del_flag == '0',
                KnowledgeBase.public_flag == '1',
                KnowledgeBase.del_flag == '0',
            )
        )
        if keyword:
            base = base.where(Document.file_name.ilike(f'%{keyword}%'))
        if kb_id:
            base = base.where(Document.kb_id == kb_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        data_q = base.order_by(Document.upload_time.desc()).offset(
            (page_num - 1) * page_size
        ).limit(page_size)
        items = list((await db.execute(data_q)).scalars().all())
        return items, total

    @classmethod
    async def add(cls, db: AsyncSession, document: Document) -> Document:
        """
        新增文档
        :param db: orm对象
        :param document: 文档对象
        :return: 文档对象
        """
        db.add(document)
        await db.flush()
        return document

    @classmethod
    async def update(cls, db: AsyncSession, document: Document) -> Document:
        """
        更新文档
        :param db: orm对象
        :param document: 文档对象（需包含 doc_id）
        :return: 文档对象
        """
        await db.merge(document)
        #merge（）方法会根据doc_id判断是新增还是更新
        #如果doc_id不存在，会新增
        #如果doc_id存在，会更新
        await db.flush()
        return document

    @classmethod
    async def delete(cls, db: AsyncSession, doc_id: str) -> None:
        """
        软删除文档（标记 del_flag = '2'）
        :param db: orm对象
        :param doc_id: 文档主键
        """
        await db.execute(
            update(Document).where(Document.doc_id == doc_id).values(del_flag='2')
        )
        await db.flush()

    @classmethod
    async def delete_hard(cls, db: AsyncSession, doc_id: str) -> None:
        """
        硬删除文档（从数据库彻底删除）
        :param db: orm对象
        :param doc_id: 文档主键
        """
        document = await cls.get_by_id(db, doc_id)
        if document:
            await db.delete(document)
            await db.flush()

    @classmethod
    async def count(cls, db: AsyncSession, **filters) -> int:
        """
        统计文档数量
        :param db: orm对象
        :param filters: 过滤条件
        :return: 数量
        """
        query = select(Document).where(Document.del_flag == '0')
        for key, value in filters.items():
            if value is not None and hasattr(Document, key):
                query = query.where(getattr(Document, key) == value)
        result = await db.execute(query)
        return len(result.scalars().all())

    @classmethod
    async def get_by_scope(
        cls, db: AsyncSession, scope: str, user_id: int | None = None, dept_id: int | None = None, limit: int = 50
    ) -> list[Document]:
        """
        按范围查询文档列表
        :param scope: personal（个人文档）或 public（公共文档）
        :param user_id: 当前用户ID（personal 时使用）
        :param dept_id: 当前部门ID（public 时使用）
        :param limit: 返回条数
        """
        from sqlalchemy import select, join
        from app.models.knowledge_base import KnowledgeBase

        if scope == 'personal':
            base = (
                select(Document)
                .where(Document.del_flag == '0', Document.uploader_id == user_id)
            )
        elif scope == 'public':
            #公开范围是以知识库KnowledgeBase为单位的（全校公开，不分部门）
            conditions = [
                Document.del_flag == '0',
                KnowledgeBase.public_flag == '1',
                KnowledgeBase.del_flag == '0',
            ]
            base = (
                select(Document)
                .join(KnowledgeBase, Document.kb_id == KnowledgeBase.kb_id)
                .where(*conditions)
            )
        else:
            return []

        base = base.order_by(Document.upload_time.desc()).limit(limit)
        result = await db.execute(base)
        return list(result.scalars().all())
