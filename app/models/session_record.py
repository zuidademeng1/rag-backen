from sqlalchemy import String, Text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

"""所有会话的消息记录汇总表"""
class SessionRecord(Base):
    __tablename__ = "ai_session_record"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)#谁说的
    content: Mapped[str] = mapped_column(Text, nullable=False)#说了啥
    msg_index: Mapped[int] = mapped_column(Integer, default=0)#消息在会话里的序号（第 0 条、第 1 条...）msg_index 记录了消息顺序，方便下次按顺序读出来当上下文。
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    create_by: Mapped[str | None] = mapped_column(String(64), default="")
    create_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), server_default=func.now())
    remark: Mapped[str | None] = mapped_column(String(500), default=None)
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
