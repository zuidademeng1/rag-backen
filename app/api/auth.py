from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from sqlalchemy import text

from app.config.config import settings
from app.core.database import AsyncSessionLocal
from app.schemas.auth import (
    LoginRequest, LoginResponse, UserInfo, RouteItem, RouteMeta,
)
from app.utils.auth_util import AuthUtil, CurrentUser
from app.utils.response_util import ResponseUtil

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
async def login(body: LoginRequest):
    print("用户登录")
    async with AsyncSessionLocal() as db:
        sql = text("""
            SELECT u.user_id, u.user_name, u.nick_name, u.password,
                   u.dept_id, u.status, u.del_flag,
                   d.dept_name
            FROM sys_user u
            LEFT JOIN sys_dept d ON u.dept_id = d.dept_id AND d.status = '0' AND d.del_flag = '0'
            WHERE u.user_name = :username
        """)
        result = await db.execute(sql, {"username": body.username})
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")

    if row.status != '0' or row.del_flag != '0':
        raise HTTPException(status_code=401, detail="用户已被禁用")

    if not bcrypt.checkpw(body.password.encode("utf-8"), row.password.encode("utf-8")):
        raise HTTPException(status_code=401, detail="密码错误")

    # 查询角色和权限
    role_sql = text("""
        SELECT r.role_key, r.data_scope
        FROM sys_user_role ur
        JOIN sys_role r ON ur.role_id = r.role_id
        WHERE ur.user_id = :uid AND r.del_flag = '0' AND r.status = '0'
    """)
    roles_result = await db.execute(role_sql, {"uid": row.user_id})
    role_rows = roles_result.fetchall()
    roles = [r.role_key for r in role_rows]
    data_scope = min((r.data_scope for r in role_rows), default="5")

    perms_sql = text("""
        SELECT DISTINCT m.perms
        FROM sys_user_role ur
        JOIN sys_role_menu rm ON ur.role_id = rm.role_id
        JOIN sys_menu m ON rm.menu_id = m.menu_id
        WHERE ur.user_id = :uid
          AND m.perms IS NOT NULL AND m.perms != ''
          AND m.status = '0'
    """)
    perms_result = await db.execute(perms_sql, {"uid": row.user_id})
    # 提取权限列表
    permissions = [p.perms for p in perms_result.fetchall()]

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    session_id = str(uuid4())
    payload = {
        "user_id": str(row.user_id),
        "user_name": row.user_name,
        "nick_name": row.nick_name,
        "dept_id": row.dept_id,
        "dept_name": row.dept_name,
        "roles": roles,
        "permissions": permissions,
        "data_scope": data_scope,
        "session_id": session_id,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    return ResponseUtil.success(data=LoginResponse(
        token=token,
        user=UserInfo(
            user_id=row.user_id,
            user_name=row.user_name,
            nick_name=row.nick_name,
            dept_id=row.dept_id,
            dept_name=row.dept_name,
            roles=roles,
            permissions=permissions,
        ),
    ))

 
@router.get("/getInfo")
async def get_info(user: CurrentUser = Depends(AuthUtil.get_current_user)):
    """获取当前用户信息（角色、权限）"""
    return ResponseUtil.success(data=UserInfo(
        user_id=user.user_id,
        user_name=user.user_name,
        nick_name=user.nick_name,
        dept_id=user.dept_id,
        dept_name=user.dept_name,
        roles=user.roles,
        permissions=user.permissions,
    ))


def _build_menu_tree(menus: list[dict], parent_id: int = 0) -> list[RouteItem]:
    """将扁平菜单列表递归构建为路由树"""
    tree: list[RouteItem] = []
    for m in menus:
        if m["parent_id"] != parent_id:
            continue
        children = _build_menu_tree(menus, m["menu_id"])
        path = m["path"] or ""
        # 顶层路由 path 必须以 "/" 开头，否则前端 Vue Router 动态注册会失败
        if parent_id == 0 and path and not path.startswith("/"):
            path = "/" + path
        item = RouteItem(
            path=path,
            component=m["component"] if m["menu_type"] != "M" else None,
            name=m.get("route_name") or m["menu_name"],
            meta=RouteMeta(
                title=m["menu_name"],
                icon=m.get("icon") or "#",
                menu_type=m["menu_type"],
                perms=m.get("perms") or "",
            ),
            children=children,
            redirect=children[0].path if children and m["menu_type"] == "M" else None,
        )
        tree.append(item)
    return tree


@router.get("/getRouters")
async def get_routers(user: CurrentUser = Depends(AuthUtil.get_current_user)):
    """获取当前用户可见的菜单路由树"""
    async with AsyncSessionLocal() as db:
        if user.is_admin:
            sql = text("""
                SELECT menu_id, menu_name, parent_id, order_num,
                       path, component, route_name, menu_type, icon, perms
                FROM sys_menu
                WHERE menu_type IN ('M', 'C') AND status = '0'
                ORDER BY parent_id, order_num
            """)
            rows = (await db.execute(sql)).fetchall()
        else:
            sql = text("""
                SELECT DISTINCT m.menu_id, m.menu_name, m.parent_id, m.order_num,
                       m.path, m.component, m.route_name, m.menu_type, m.icon, m.perms
                FROM sys_menu m
                JOIN sys_role_menu rm ON m.menu_id = rm.menu_id
                JOIN sys_user_role ur ON rm.role_id = ur.role_id
                WHERE ur.user_id = :uid
                  AND m.menu_type IN ('M', 'C')
                  AND m.status = '0'
                ORDER BY m.parent_id, m.order_num
            """)
            rows = (await db.execute(sql, {"uid": user.user_id})).fetchall()

    menus = [dict(r._mapping) for r in rows]
    tree = _build_menu_tree(menus)
    return ResponseUtil.success(data=tree)
