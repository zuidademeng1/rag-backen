from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk


class DocumentChunkDao:
#批量插入文档分块到数据库中
    @classmethod
    async def batch_insert(cls, db: AsyncSession, chunks: list[DocumentChunk]) -> None:
        db.add_all(chunks)
        await db.flush()
