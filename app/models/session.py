from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

"""会话的目录表"""
class Session(Base):
    __tablename__ = "ai_session"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)#数字主键，机器用来过滤/关联的，这个会话的所属用户id，，表示"这个会话是谁的"，既用于归属，也用于权限隔离——每个用户只能查自己的会话。
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    dept_id: Mapped[str | None] = mapped_column(String(64), default=None)
    create_by: Mapped[str | None] = mapped_column(String(64), default="")#用户名，可读名字，审计字段用来给人看是谁操作的。
    create_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), server_default=func.now())
    update_by: Mapped[str | None] = mapped_column(String(64), default="")
    update_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=False), onupdate=func.now())
    remark: Mapped[str | None] = mapped_column(String(500), default=None)
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
