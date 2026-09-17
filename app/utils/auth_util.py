from dataclasses import dataclass, field

from fastapi import Request, HTTPException
from jose import jwt, JWTError
from sqlalchemy import text

from app.config.config import settings
from app.core.database import AsyncSessionLocal


@dataclass
class CurrentUser:
    """当前登录用户"""
    user_id: int
    user_name: str
    nick_name: str = ""
    dept_id: int | None = None
    dept_name: str | None = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    data_scope: str = "5"

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


class AuthUtil:
    """认证工具类，提供当前用户信息获取"""

    _payload_cache: dict | None = None

    @classmethod
    def _decode_token(cls, request: Request) -> dict:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="未登录或token无效")
        try:
            return jwt.decode(
                auth[7:], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm],
            )
        except JWTError:
            raise HTTPException(status_code=401, detail="token已过期或无效")

    @classmethod
    async def get_current_user(cls, request: Request) -> CurrentUser:
        """获取当前登录用户（FastAPI Depends 可用）"""
        payload = cls._decode_token(request)
        user_id = int(payload.get("user_id", 0))
        if not user_id:
            raise HTTPException(status_code=401, detail="token无效")

        # 优先从 JWT payload 获取
        user_name = payload.get("user_name", "")
        dept_id = payload.get("dept_id")
        dept_name = payload.get("dept_name")
        roles = payload.get("roles", [])
        permissions = payload.get("permissions", [])

        # 如果 JWT 里信息不全，从数据库补全
        if not dept_id or not roles:
            async with AsyncSessionLocal() as db:
                sql = text("""
                    SELECT u.user_name, u.nick_name, u.dept_id, d.dept_name
                    FROM sys_user u
                    LEFT JOIN sys_dept d ON u.dept_id = d.dept_id
                    WHERE u.user_id = :uid AND u.del_flag = '0'
                """)
                row = (await db.execute(sql, {"uid": user_id})).fetchone()
                if not row:
                    raise HTTPException(status_code=401, detail="用户不存在")
                user_name = row.user_name
                nick_name = row.nick_name or ""
                dept_id = row.dept_id
                dept_name = row.dept_name

                roles_sql = text("""
                    SELECT r.role_key, r.data_scope
                    FROM sys_user_role ur
                    JOIN sys_role r ON ur.role_id = r.role_id
                    WHERE ur.user_id = :uid AND r.del_flag = '0' AND r.status = '0'
                """)
                roles_result = (await db.execute(roles_sql, {"uid": user_id})).fetchall()
                roles = [r.role_key for r in roles_result]
                data_scope = min((r.data_scope for r in roles_result), default="5")

                # 查询权限标识
                perms_sql = text("""
                    SELECT DISTINCT m.perms
                    FROM sys_user_role ur
                    JOIN sys_role_menu rm ON ur.role_id = rm.role_id
                    JOIN sys_menu m ON rm.menu_id = m.menu_id
                    WHERE ur.user_id = :uid
                      AND m.perms IS NOT NULL AND m.perms != ''
                      AND m.status = '0'
                """)
                perms_result = (await db.execute(perms_sql, {"uid": user_id})).fetchall()
                permissions = [p.perms for p in perms_result]
        else:
            nick_name = payload.get("nick_name", user_name)
            data_scope = payload.get("data_scope", "3")

        return CurrentUser(
            user_id=user_id, user_name=user_name, nick_name=nick_name,
            dept_id=dept_id, dept_name=dept_name,
            roles=roles, permissions=permissions, data_scope=data_scope,
        )

    @classmethod
    async def get_user_id(cls, request: Request) -> int:
        """获取当前登录用户主键"""
        return int(cls._decode_token(request).get("user_id", 0))

    @classmethod
    async def get_user_name(cls, request: Request) -> str:
        """获取当前登录用户名称"""
        payload = cls._decode_token(request)
        name = payload.get("user_name", "")
        if not name:
            user = await cls.get_current_user(request)
            name = user.user_name
        return name

    @classmethod
    async def get_user_dept(cls, request: Request) -> tuple[int | None, str | None]:
        """获取当前登录用户部门 (dept_id, dept_name)"""
        payload = cls._decode_token(request)
        dept_id = payload.get("dept_id")
        dept_name = payload.get("dept_name")
        if not dept_id:
            async with AsyncSessionLocal() as db:
                sql = text("""
                    SELECT u.dept_id, d.dept_name
                    FROM sys_user u
                    LEFT JOIN sys_dept d ON u.dept_id = d.dept_id
                    WHERE u.user_id = :uid
                """)
                row = (await db.execute(sql, {"uid": int(payload.get("user_id", 0))})).fetchone()
                if row:
                    dept_id, dept_name = row.dept_id, row.dept_name
        return dept_id, dept_name
