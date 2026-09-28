from sqlalchemy import String, Text, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

"""文档表"""
class Document(Base):
    __tablename__ = "ai_document"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(20), default=None)
    file_size: Mapped[int | None] = mapped_column(BigInteger, default=None)
    file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    file_ext: Mapped[str | None] = mapped_column(String(20), default=None)#文件拓展名（后缀）（如 .pdf、.docx 等）
    kb_id: Mapped[str | None] = mapped_column(String(64), default=None)#知识库 ID
    chunk_status: Mapped[str | None] = mapped_column(String(20), default="pending")
    upload_by: Mapped[str | None] = mapped_column(String(64), default="")
    uploader_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    upload_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), server_default=func.now())
    dept_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    update_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), onupdate=func.now())
    remark: Mapped[str | None] = mapped_column(String(500), default=None)
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
