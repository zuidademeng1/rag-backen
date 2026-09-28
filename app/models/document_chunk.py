from sqlalchemy import String, Text, Integer, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

"""文档分块表"""
class DocumentChunk(Base):
    __tablename__ = "ai_document_chunk"

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)#分块的全局唯一 ID，用来唯一定位这一行
    doc_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)#分块在所属文档里的序号（第 0 块、第 1 块...）
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str | None] = mapped_column(String(256), default=None)
    char_count: Mapped[int | None] = mapped_column(Integer, default=0)
    dept_id: Mapped[str] = mapped_column(String(64))
    create_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), server_default=func.now())
    update_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), onupdate=func.now())
    remark: Mapped[str | None] = mapped_column(String(500), default=None)
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
