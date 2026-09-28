from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

"""用户表"""
class SysUser(Base):
    __tablename__ = "sys_user"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dept_id: Mapped[int | None] = mapped_column(BigInteger)
    user_name: Mapped[str] = mapped_column(String)
    nick_name: Mapped[str] = mapped_column(String)
    user_type: Mapped[str | None] = mapped_column(String, default="00")
    email: Mapped[str | None] = mapped_column(String, default="")
    phonenumber: Mapped[str | None] = mapped_column(String, default="")
    sex: Mapped[str | None] = mapped_column(String(1), default="0")
    avatar: Mapped[str | None] = mapped_column(String, default="")
    password: Mapped[str | None] = mapped_column(String, default="")
    status: Mapped[str | None] = mapped_column(String(1), default="0")
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
    login_ip: Mapped[str | None] = mapped_column(String, default="")
    login_date: Mapped[datetime | None] = mapped_column(DateTime)
    create_by: Mapped[str | None] = mapped_column(String, default="")
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_by: Mapped[str | None] = mapped_column(String, default="")
    update_time: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String)

"""角色表"""
class SysRole(Base):
    __tablename__ = "sys_role"

    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_name: Mapped[str] = mapped_column(String)
    role_key: Mapped[str] = mapped_column(String)
    role_sort: Mapped[int] = mapped_column(Integer)
    data_scope: Mapped[str | None] = mapped_column(String(1), default="1")
    menu_check_strictly: Mapped[int | None] = mapped_column(SmallInteger, default=1)
    dept_check_strictly: Mapped[int | None] = mapped_column(SmallInteger, default=1)
    status: Mapped[str] = mapped_column(String(1))
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
    create_by: Mapped[str | None] = mapped_column(String, default="")
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_by: Mapped[str | None] = mapped_column(String, default="")
    update_time: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String)

"""菜单/权限表"""
class SysMenu(Base):
    __tablename__ = "sys_menu"

    menu_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    menu_name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, default=0)
    order_num: Mapped[int | None] = mapped_column(Integer, default=0)
    path: Mapped[str | None] = mapped_column(String, default="")
    component: Mapped[str | None] = mapped_column(String)
    query: Mapped[str | None] = mapped_column(String)
    route_name: Mapped[str | None] = mapped_column(String, default="")
    is_frame: Mapped[int | None] = mapped_column(Integer, default=1)
    is_cache: Mapped[int | None] = mapped_column(Integer, default=0)
    menu_type: Mapped[str | None] = mapped_column(String(1), default="")
    visible: Mapped[str | None] = mapped_column(String(1), default="0")
    status: Mapped[str | None] = mapped_column(String(1), default="0")
    perms: Mapped[str | None] = mapped_column(String)
    icon: Mapped[str | None] = mapped_column(String, default="#")
    create_by: Mapped[str | None] = mapped_column(String, default="")
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_by: Mapped[str | None] = mapped_column(String, default="")
    update_time: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String, default="")

"""部门表"""
class SysDept(Base):
    __tablename__ = "sys_dept"

    dept_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, default=0)#里面存的是父部门的dept_id
    ancestors: Mapped[str | None] = mapped_column(String, default="")
    dept_name: Mapped[str | None] = mapped_column(String, default="")
    order_num: Mapped[int | None] = mapped_column(Integer, default=0)
    leader: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String(1), default="0")
    del_flag: Mapped[str | None] = mapped_column(String(1), default="0")
    create_by: Mapped[str | None] = mapped_column(String, default="")
    create_time: Mapped[datetime | None] = mapped_column(DateTime)
    update_by: Mapped[str | None] = mapped_column(String, default="")
    update_time: Mapped[datetime | None] = mapped_column(DateTime)
