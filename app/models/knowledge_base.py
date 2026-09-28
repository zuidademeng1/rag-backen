from sqlalchemy import String, Text, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

"""知识库表"""
class KnowledgeBase(Base):
    __tablename__ = "ai_knowledge_base"

    kb_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kb_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kb_desc: Mapped[str | None] = mapped_column(Text, default=None)
    kb_icon: Mapped[str | None] = mapped_column(String(100), default=None)
    public_flag: Mapped[str | None] = mapped_column(String(1))
    user_id: Mapped[str | None] = mapped_column(String(64), default=None)
    dept_id: Mapped[str | None] = mapped_column(String(64), default=None)
    create_by: Mapped[str | None] = mapped_column(String(64), default="")
    create_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), server_default=func.now())
    update_by: Mapped[str | None] = mapped_column(String(64), default="")
    update_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), onupdate=func.now())
    remark: Mapped[str | None] = mapped_column(String(500), default=None)
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
