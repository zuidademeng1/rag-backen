import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permission import RequirePermission
from app.schemas.system import (
    UserQuery, UserCreate, UserUpdate, UserEntity,
    ResetPwd, AuthRoleBody,
    RoleQuery, RoleCreate, RoleUpdate, RoleEntity, MenuTreeBody,
    MenuQuery, MenuCreate, MenuUpdate, MenuEntity, MenuTreeItem,
    DeptQuery, DeptCreate, DeptUpdate, DeptEntity,
    LoginLogQuery, LoginLogEntity, OperLogQuery, OperLogEntity,
    DictTypeQuery, DictTypeCreate, DictTypeUpdate, DictTypeEntity,
    DictDataQuery, DictDataCreate, DictDataUpdate, DictDataEntity,
)
from app.utils.auth_util import AuthUtil, CurrentUser
from app.utils.response_util import ResponseUtil

router = APIRouter(prefix="/system", tags=["系统管理"])


# ======================== 用户管理 ========================

@router.get("/user/list")
async def user_list(
    query: UserQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:list")),
):
    conditions = ["u.del_flag = '0'"]
    params: dict = {}

    if query.user_name:
        conditions.append("u.user_name LIKE :userName")
        params["userName"] = f"%{query.user_name}%"
    if query.status:
        conditions.append("u.status = :status")
        params["status"] = query.status
    if query.dept_id:
        conditions.append("u.dept_id = :deptId")
        params["deptId"] = query.dept_id

    where = " AND ".join(conditions)

    count_sql = text(f"SELECT COUNT(*) FROM sys_user u WHERE {where}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    offset = (query.page_num - 1) * query.page_size
    data_sql = text(f"""
        SELECT u.user_id, u.user_name, u.nick_name, u.dept_id, d.dept_name,
               u.email, d.phone, u.sex, u.status, u.create_time
        FROM sys_user u
        LEFT JOIN sys_dept d ON u.dept_id = d.dept_id AND d.del_flag = '0'
        WHERE {where}
        ORDER BY u.user_id
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = query.page_size
    params["offset"] = offset
    rows = (await db.execute(data_sql, params)).fetchall()

    result = []
    for r in rows:
        # get role ids
        role_sql = text("SELECT role_id FROM sys_user_role WHERE user_id = :uid")
        role_ids = [row[0] for row in (await db.execute(role_sql, {"uid": r.user_id})).fetchall()]
        result.append(UserEntity(
            user_id=r.user_id, user_name=r.user_name, nick_name=r.nick_name,
            dept_id=r.dept_id, dept_name=r.dept_name,
            email=r.email, phone=r.phone, sex=r.sex, status=r.status,
            create_time=r.create_time, role_ids=role_ids,
        ).model_dump(by_alias=True, mode="json"))

    return ResponseUtil.paginate(rows=result, total=total, page_num=query.page_num, page_size=query.page_size)


@router.get("/user/{user_id}")
async def user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:list")),
):
    sql = text("""
        SELECT u.user_id, u.user_name, u.nick_name, u.dept_id, d.dept_name,
               u.email, d.phone, u.sex, u.status, u.create_time
        FROM sys_user u
        LEFT JOIN sys_dept d ON u.dept_id = d.dept_id AND d.del_flag = '0'
        WHERE u.user_id = :uid AND u.del_flag = '0'
    """)
    row = (await db.execute(sql, {"uid": user_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    role_sql = text("SELECT role_id FROM sys_user_role WHERE user_id = :uid")
    role_ids = [r[0] for r in (await db.execute(role_sql, {"uid": user_id})).fetchall()]

    entity = UserEntity(
        user_id=row.user_id, user_name=row.user_name, nick_name=row.nick_name,
        dept_id=row.dept_id, dept_name=row.dept_name,
        email=row.email, phone=row.phone, sex=row.sex, status=row.status,
        create_time=row.create_time, role_ids=role_ids,
    )
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json"))


@router.post("/user/add")
async def user_add(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:add")),
):
    # check unique
    check = await db.execute(text("SELECT user_id FROM sys_user WHERE user_name = :un AND del_flag = '0'"), {"un": body.user_name})
    if check.fetchone():
        raise HTTPException(status_code=400, detail="用户名已存在")

    hashed = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt())
    now = "now()"
    insert_sql = text(f"""
        INSERT INTO sys_user (user_name, nick_name, password, dept_id, email, sex, status, create_time, del_flag)
        VALUES (:un, :nn, :pw, :did, :em, :sx, :st, {now}, '0')
        RETURNING user_id
    """)
    new_id = (await db.execute(insert_sql, {
        "un": body.user_name, "nn": body.nick_name, "pw": hashed.decode("utf-8"),
        "did": body.dept_id, "em": body.email,
        "sx": body.sex, "st": body.status,
    })).scalar_one()

    # assign roles
    if body.role_ids:
        values = ", ".join(f"({new_id}, {rid})" for rid in body.role_ids)
        await db.execute(text(f"INSERT INTO sys_user_role (user_id, role_id) VALUES {values} ON CONFLICT DO NOTHING"))

    await db.commit()
    return ResponseUtil.success(msg="新增成功")


@router.put("/user/update")
async def user_update(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:edit")),
):
    check = await db.execute(text("SELECT user_id FROM sys_user WHERE user_id = :uid AND del_flag = '0'"), {"uid": body.user_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="用户不存在")

    # check unique except self
    dup = await db.execute(
        text("SELECT user_id FROM sys_user WHERE user_name = :un AND user_id != :uid AND del_flag = '0'"),
        {"un": body.user_name, "uid": body.user_id},
    )
    if dup.fetchone():
        raise HTTPException(status_code=400, detail="用户名已被其他用户使用")

    if body.password:
        hashed = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt())
        pw_part = "password = :pw,"
        pw_param = {"pw": hashed.decode("utf-8")}
    else:
        pw_part = ""
        pw_param = {}

    update_sql = text(f"""
        UPDATE sys_user SET
            user_name = :un, nick_name = :nn, dept_id = :did,
            email = :em, sex = :sx, status = :st,
            {pw_part}
            update_time = now()
        WHERE user_id = :uid
    """)
    await db.execute(update_sql, {
        "un": body.user_name, "nn": body.nick_name, "did": body.dept_id,
        "em": body.email, "sx": body.sex, "st": body.status,
        **pw_param, "uid": body.user_id,
    })

    # re-assign roles
    await db.execute(text("DELETE FROM sys_user_role WHERE user_id = :uid"), {"uid": body.user_id})
    if body.role_ids:
        values = ", ".join(f"({body.user_id}, {rid})" for rid in body.role_ids)
        await db.execute(text(f"INSERT INTO sys_user_role (user_id, role_id) VALUES {values}"))

    await db.commit()
    return ResponseUtil.success(msg="更新成功")


@router.delete("/user/delete/{user_id}")
async def user_delete(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:delete")),
):
    if user_id == 1:
        raise HTTPException(status_code=400, detail="不能删除超级管理员")
    check = await db.execute(text("SELECT user_id FROM sys_user WHERE user_id = :uid AND del_flag = '0'"), {"uid": user_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="用户不存在")

    await db.execute(text("UPDATE sys_user SET del_flag = '2' WHERE user_id = :uid"), {"uid": user_id})
    await db.execute(text("DELETE FROM sys_user_role WHERE user_id = :uid"), {"uid": user_id})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")


@router.put("/user/resetPwd")
async def user_reset_pwd(
    body: ResetPwd,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:resetPwd")),
):
    hashed = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt())
    await db.execute(
        text("UPDATE sys_user SET password = :pw WHERE user_id = :uid"),
        {"pw": hashed.decode("utf-8"), "uid": body.user_id},
    )
    await db.commit()
    return ResponseUtil.success(msg="重置成功")


@router.get("/user/authRole/{user_id}")
async def user_auth_role(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:authRole")),
):
    # all roles
    all_sql = text("SELECT role_id, role_name, role_key FROM sys_role WHERE del_flag = '0' AND status = '0'")
    all_roles = [dict(r._mapping) for r in (await db.execute(all_sql)).fetchall()]

    # user's assigned role ids
    assigned_sql = text("SELECT role_id FROM sys_user_role WHERE user_id = :uid")
    assigned_ids = [r[0] for r in (await db.execute(assigned_sql, {"uid": user_id})).fetchall()]

    return ResponseUtil.success(data={
        "roles": all_roles,
        "assignedRoleIds": assigned_ids,
    })


@router.put("/user/authRole")
async def user_auth_role_update(
    body: AuthRoleBody,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:user:authRole")),
):
    await db.execute(text("DELETE FROM sys_user_role WHERE user_id = :uid"), {"uid": body.user_id})
    if body.role_ids:
        values = ", ".join(f"({body.user_id}, {rid})" for rid in body.role_ids)
        await db.execute(text(f"INSERT INTO sys_user_role (user_id, role_id) VALUES {values}"))
    await db.commit()
    return ResponseUtil.success(msg="分配成功")


# ======================== 角色管理 ========================

@router.get("/role/list")
async def role_list(
    query: RoleQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:role:list")),
):
    conditions = ["r.del_flag = '0'"]
    params: dict = {}

    if query.role_name:
        conditions.append("r.role_name LIKE :roleName")
        params["roleName"] = f"%{query.role_name}%"
    if query.status:
        conditions.append("r.status = :status")
        params["status"] = query.status

    where = " AND ".join(conditions)

    count_sql = text(f"SELECT COUNT(*) FROM sys_role r WHERE {where}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    offset = (query.page_num - 1) * query.page_size
    data_sql = text(f"""
        SELECT role_id, role_name, role_key, role_sort, status, create_time
        FROM sys_role r
        WHERE {where}
        ORDER BY role_sort
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = query.page_size
    params["offset"] = offset
    rows = (await db.execute(data_sql, params)).fetchall()

    result = [RoleEntity(
        role_id=r.role_id, role_name=r.role_name, role_key=r.role_key,
        role_sort=r.role_sort, status=r.status, create_time=r.create_time,
    ).model_dump(by_alias=True, mode="json") for r in rows]

    return ResponseUtil.paginate(rows=result, total=total, page_num=query.page_num, page_size=query.page_size)


@router.get("/role/{role_id}")
async def role_detail(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:role:list")),
):
    sql = text("SELECT role_id, role_name, role_key, role_sort, status, create_time FROM sys_role WHERE role_id = :rid AND del_flag = '0'")
    row = (await db.execute(sql, {"rid": role_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="角色不存在")

    entity = RoleEntity(
        role_id=row.role_id, role_name=row.role_name, role_key=row.role_key,
        role_sort=row.role_sort, status=row.status, create_time=row.create_time,
    )
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json"))


@router.post("/role/add")
async def role_add(
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:role:add")),
):
    dup = await db.execute(text("SELECT role_id FROM sys_role WHERE role_key = :rk AND del_flag = '0'"), {"rk": body.role_key})
    if dup.fetchone():
        raise HTTPException(status_code=400, detail="角色标识已存在")

    insert_sql = text("""
        INSERT INTO sys_role (role_name, role_key, role_sort, status, create_time, del_flag)
        VALUES (:rn, :rk, :rs, :st, now(), '0')
        RETURNING role_id
    """)
    new_id = (await db.execute(insert_sql, {
        "rn": body.role_name, "rk": body.role_key, "rs": body.role_sort, "st": body.status,
    })).scalar_one()

    if body.menu_ids:
        values = ", ".join(f"({new_id}, {mid})" for mid in body.menu_ids)
        await db.execute(text(f"INSERT INTO sys_role_menu (role_id, menu_id) VALUES {values} ON CONFLICT DO NOTHING"))

    await db.commit()
    return ResponseUtil.success(msg="新增成功")


@router.put("/role/update")
async def role_update(
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:role:edit")),
):
    check = await db.execute(text("SELECT role_id FROM sys_role WHERE role_id = :rid AND del_flag = '0'"), {"rid": body.role_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="角色不存在")

    dup = await db.execute(
        text("SELECT role_id FROM sys_role WHERE role_key = :rk AND role_id != :rid AND del_flag = '0'"),
        {"rk": body.role_key, "rid": body.role_id},
    )
    if dup.fetchone():
        raise HTTPException(status_code=400, detail="角色标识已被其他角色使用")

    await db.execute(text("""
        UPDATE sys_role SET role_name = :rn, role_key = :rk, role_sort = :rs, status = :st, update_time = now()
        WHERE role_id = :rid
    """), {"rn": body.role_name, "rk": body.role_key, "rs": body.role_sort, "st": body.status, "rid": body.role_id})

    # re-assign menus
    await db.execute(text("DELETE FROM sys_role_menu WHERE role_id = :rid"), {"rid": body.role_id})
    if body.menu_ids:
        values = ", ".join(f"({body.role_id}, {mid})" for mid in body.menu_ids)
        await db.execute(text(f"INSERT INTO sys_role_menu (role_id, menu_id) VALUES {values}"))

    await db.commit()
    return ResponseUtil.success(msg="更新成功")


@router.delete("/role/delete/{role_id}")
async def role_delete(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:role:delete")),
):
    if role_id == 1:
        raise HTTPException(status_code=400, detail="不能删除超级管理员角色")
    check = await db.execute(text("SELECT role_id FROM sys_role WHERE role_id = :rid AND del_flag = '0'"), {"rid": role_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="角色不存在")

    # check if role is assigned to any user
    user_check = await db.execute(text("SELECT user_id FROM sys_user_role WHERE role_id = :rid LIMIT 1"), {"rid": role_id})
    if user_check.fetchone():
        raise HTTPException(status_code=400, detail="该角色已分配给用户，不能删除")

    await db.execute(text("UPDATE sys_role SET del_flag = '2' WHERE role_id = :rid"), {"rid": role_id})
    await db.execute(text("DELETE FROM sys_role_menu WHERE role_id = :rid"), {"rid": role_id})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")


@router.get("/role/menuTree/{role_id}")
async def role_menu_tree(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:role:list")),
):
    # all menus as flat list
    menus_sql = text("""
        SELECT menu_id, menu_name, parent_id FROM sys_menu
        WHERE menu_type IN ('M', 'C') AND status = '0'
        ORDER BY parent_id, order_num
    """)
    all_menus = [dict(r._mapping) for r in (await db.execute(menus_sql)).fetchall()]

    # assigned menu ids for the role
    assigned_sql = text("SELECT menu_id FROM sys_role_menu WHERE role_id = :rid")
    assigned_ids = set(r[0] for r in (await db.execute(assigned_sql, {"rid": role_id})).fetchall())

    # build tree
    tree = _build_menu_tree_items(all_menus, 0, assigned_ids)
    return ResponseUtil.success(data={
        "menus": tree,
        "checkedKeys": list(assigned_ids),
    })


def _build_menu_tree_items(menus: list[dict], parent_id: int, checked: set[int]) -> list:
    result = []
    for m in menus:
        if m["parent_id"] != parent_id:
            continue
        children = _build_menu_tree_items(menus, m["menu_id"], checked)
        item = MenuTreeItem(
            id=m["menu_id"],
            label=m["menu_name"],
            children=children,
        )
        result.append(item)
    return result


@router.put("/role/menuTree")
async def role_menu_tree_update(
    body: MenuTreeBody,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:role:edit")),
):
    await db.execute(text("DELETE FROM sys_role_menu WHERE role_id = :rid"), {"rid": body.role_id})
    if body.menu_ids:
        values = ", ".join(f"({body.role_id}, {mid})" for mid in body.menu_ids)
        await db.execute(text(f"INSERT INTO sys_role_menu (role_id, menu_id) VALUES {values}"))
    await db.commit()
    return ResponseUtil.success(msg="分配成功")


# ======================== 菜单管理 ========================

@router.get("/menu/list")
async def menu_list(
    query: MenuQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:menu:list")),
):
    conditions = ["m.menu_type IN ('M', 'C', 'F')"]
    params: dict = {}

    if query.menu_name:
        conditions.append("m.menu_name LIKE :menuName")
        params["menuName"] = f"%{query.menu_name}%"
    if query.status:
        conditions.append("m.status = :status")
        params["status"] = query.status

    where = " AND ".join(conditions)
    sql = text(f"""
        SELECT menu_id, menu_name, parent_id, order_num, path, component,
               route_name, menu_type, visible, status, perms, icon, is_frame, is_cache
        FROM sys_menu m
        WHERE {where}
        ORDER BY parent_id, order_num
    """)
    rows = [dict(r._mapping) for r in (await db.execute(sql, params)).fetchall()]

    tree = _build_menu_entity_tree(rows, 0)

    return ResponseUtil.success(data=tree)


def _build_menu_entity_tree(menus: list[dict], parent_id: int) -> list:
    result = []
    for m in menus:
        if m["parent_id"] != parent_id:
            continue
        children = _build_menu_entity_tree(menus, m["menu_id"])
        entity = MenuEntity(
            menu_id=m["menu_id"], menu_name=m["menu_name"],
            parent_id=m["parent_id"], order_num=m["order_num"],
            path=m["path"], component=m["component"],
            route_name=m.get("route_name"), menu_type=m["menu_type"],
            visible=m["visible"], status=m["status"], perms=m.get("perms"),
            icon=m.get("icon"), is_frame=m["is_frame"], is_cache=m["is_cache"],
            children=children,
        )
        result.append(entity.model_dump(by_alias=True, mode="json"))
    return result


@router.get("/menu/{menu_id}")
async def menu_detail(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:menu:list")),
):
    sql = text("""
        SELECT menu_id, menu_name, parent_id, order_num, path, component,
               route_name, menu_type, visible, status, perms, icon, is_frame, is_cache
        FROM sys_menu WHERE menu_id = :mid
    """)
    row = (await db.execute(sql, {"mid": menu_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="菜单不存在")

    entity = MenuEntity(
        menu_id=row.menu_id, menu_name=row.menu_name,
        parent_id=row.parent_id, order_num=row.order_num,
        path=row.path, component=row.component,
        route_name=row.route_name, menu_type=row.menu_type,
        visible=row.visible, status=row.status, perms=row.perms,
        icon=row.icon, is_frame=row.is_frame, is_cache=row.is_cache,
    )
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json"))


@router.post("/menu/add")
async def menu_add(
    body: MenuCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:menu:add")),
):
    insert_sql = text("""
        INSERT INTO sys_menu (menu_name, parent_id, order_num, path, component,
            route_name, menu_type, visible, status, perms, icon, is_frame, is_cache, create_time)
        VALUES (:mn, :pid, :on, :pa, :co, :rn, :mt, :vi, :st, :pe, :ic, :ifr, :ica, now())
    """)
    await db.execute(insert_sql, {
        "mn": body.menu_name, "pid": body.parent_id, "on": body.order_num,
        "pa": body.path, "co": body.component, "rn": body.route_name,
        "mt": body.menu_type, "vi": body.visible, "st": body.status,
        "pe": body.perms, "ic": body.icon, "ifr": body.is_frame, "ica": body.is_cache,
    })
    await db.commit()
    return ResponseUtil.success(msg="新增成功")


@router.put("/menu/update")
async def menu_update(
    body: MenuUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:menu:edit")),
):
    check = await db.execute(text("SELECT menu_id FROM sys_menu WHERE menu_id = :mid"), {"mid": body.menu_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="菜单不存在")

    update_sql = text("""
        UPDATE sys_menu SET
            menu_name = :mn, parent_id = :pid, order_num = :on,
            path = :pa, component = :co, route_name = :rn,
            menu_type = :mt, visible = :vi, status = :st,
            perms = :pe, icon = :ic, is_frame = :ifr, is_cache = :ica,
            update_time = now()
        WHERE menu_id = :mid
    """)
    await db.execute(update_sql, {
        "mn": body.menu_name, "pid": body.parent_id, "on": body.order_num,
        "pa": body.path, "co": body.component, "rn": body.route_name,
        "mt": body.menu_type, "vi": body.visible, "st": body.status,
        "pe": body.perms, "ic": body.icon, "ifr": body.is_frame, "ica": body.is_cache,
        "mid": body.menu_id,
    })
    await db.commit()
    return ResponseUtil.success(msg="更新成功")


@router.delete("/menu/delete/{menu_id}")
async def menu_delete(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:menu:delete")),
):
    # check if has children
    child_check = await db.execute(text("SELECT menu_id FROM sys_menu WHERE parent_id = :mid LIMIT 1"), {"mid": menu_id})
    if child_check.fetchone():
        raise HTTPException(status_code=400, detail="存在子菜单，不能删除")

    check = await db.execute(text("SELECT menu_id FROM sys_menu WHERE menu_id = :mid"), {"mid": menu_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="菜单不存在")

    await db.execute(text("DELETE FROM sys_role_menu WHERE menu_id = :mid"), {"mid": menu_id})
    await db.execute(text("DELETE FROM sys_menu WHERE menu_id = :mid"), {"mid": menu_id})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")


# ======================== 部门管理 ========================


def _build_dept_entity_tree(rows: list[dict]) -> list[dict]:
    """构建部门树实体列表（children 嵌套）"""
    children_map: dict[int, list[dict]] = {}
    for r in rows:
        r["children"] = []
        pid = r.get("parent_id") or 0
        children_map.setdefault(pid, []).append(r)
    # 从 pid=0 开始递归
    result = _attach_dept_children(0, children_map)
    # 按 order_num 排序
    def sort_key(item: dict):
        return item.get("order_num") or 0
    for item in result:
        _sort_dept_children(item, sort_key)
    result.sort(key=sort_key)
    return result


def _attach_dept_children(parent_id: int, children_map: dict[int, list[dict]]) -> list[dict]:
    nodes = []
    for item in children_map.get(parent_id, []):
        item["children"] = _attach_dept_children(item["dept_id"], children_map)
        entity = DeptEntity(**item).model_dump(by_alias=True, mode="json",
            exclude_none=True)
        nodes.append(entity)
    return nodes


def _sort_dept_children(node: dict, sort_key):
    node["children"].sort(key=sort_key)
    for child in node["children"]:
        _sort_dept_children(child, sort_key)


@router.get("/dept/list")
async def dept_list(
    query: DeptQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dept:list")),
):
    conditions = ["d.del_flag = '0'"]
    params: dict = {}

    if query.dept_name:
        conditions.append("d.dept_name LIKE :deptName")
        params["deptName"] = f"%{query.dept_name}%"
    if query.status:
        conditions.append("d.status = :status")
        params["status"] = query.status

    where = " AND ".join(conditions)
    sql = text(f"""
        SELECT d.dept_id, d.parent_id, d.dept_name, d.order_num,
               d.leader, d.phone, d.email, d.status, d.create_time
        FROM sys_dept d
        WHERE {where}
        ORDER BY d.order_num
    """)
    rows = (await db.execute(sql, params)).fetchall()
    dicts = [r._asdict() for r in rows]
    tree = _build_dept_entity_tree(dicts)
    return ResponseUtil.success(data=tree)


@router.get("/dept/{dept_id}")
async def dept_detail(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dept:list")),
):
    sql = text("""
        SELECT dept_id, parent_id, dept_name, order_num,
               leader, phone, email, status, create_time
        FROM sys_dept
        WHERE dept_id = :did AND del_flag = '0'
    """)
    row = (await db.execute(sql, {"did": dept_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="部门不存在")

    entity = DeptEntity(**row._asdict())
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json", exclude_none=True))


@router.post("/dept/add")
async def dept_add(
    body: DeptCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dept:add")),
):
    dup = await db.execute(text("SELECT dept_id FROM sys_dept WHERE dept_name = :dn AND del_flag = '0'"), {"dn": body.dept_name})
    if dup.fetchone():
        raise HTTPException(status_code=400, detail="部门名称已存在")

    insert_sql = text("""
        INSERT INTO sys_dept (dept_name, parent_id, order_num, leader, phone, email, status, create_time, del_flag)
        VALUES (:dn, :pid, :on, :ld, :ph, :em, :st, now(), '0')
    """)
    await db.execute(insert_sql, {
        "dn": body.dept_name, "pid": body.parent_id, "on": body.order_num,
        "ld": body.leader, "ph": body.phone, "em": body.email, "st": body.status,
    })
    await db.commit()
    return ResponseUtil.success(msg="新增成功")


@router.put("/dept/update")
async def dept_update(
    body: DeptUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dept:edit")),
):
    check = await db.execute(text("SELECT dept_id FROM sys_dept WHERE dept_id = :did AND del_flag = '0'"), {"did": body.dept_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="部门不存在")

    dup = await db.execute(
        text("SELECT dept_id FROM sys_dept WHERE dept_name = :dn AND dept_id != :did AND del_flag = '0'"),
        {"dn": body.dept_name, "did": body.dept_id},
    )
    if dup.fetchone():
        raise HTTPException(status_code=400, detail="部门名称已被其他部门使用")

    await db.execute(text("""
        UPDATE sys_dept SET
            dept_name = :dn, parent_id = :pid, order_num = :on,
            leader = :ld, phone = :ph, email = :em, status = :st,
            update_time = now()
        WHERE dept_id = :did
    """), {
        "dn": body.dept_name, "pid": body.parent_id, "on": body.order_num,
        "ld": body.leader, "ph": body.phone, "em": body.email, "st": body.status,
        "did": body.dept_id,
    })
    await db.commit()
    return ResponseUtil.success(msg="更新成功")


@router.delete("/dept/delete/{dept_id}")
async def dept_delete(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dept:delete")),
):
    # check if has children
    child_check = await db.execute(text("SELECT dept_id FROM sys_dept WHERE parent_id = :did AND del_flag = '0' LIMIT 1"), {"did": dept_id})
    if child_check.fetchone():
        raise HTTPException(status_code=400, detail="存在子部门，不能删除")

    # check if assigned to users
    user_check = await db.execute(text("SELECT user_id FROM sys_user WHERE dept_id = :did AND del_flag = '0' LIMIT 1"), {"did": dept_id})
    if user_check.fetchone():
        raise HTTPException(status_code=400, detail="部门下存在用户，不能删除")

    check = await db.execute(text("SELECT dept_id FROM sys_dept WHERE dept_id = :did AND del_flag = '0'"), {"did": dept_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="部门不存在")

    await db.execute(text("UPDATE sys_dept SET del_flag = '2' WHERE dept_id = :did"), {"did": dept_id})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")


# ======================== 登录日志 ========================


@router.get("/loginlog/list")
async def login_log_list(
    query: LoginLogQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:list")),
):
    conditions: list[str] = []
    params: dict = {}

    if query.user_name:
        conditions.append("user_name LIKE :userName")
        params["userName"] = f"%{query.user_name}%"
    if query.status:
        conditions.append("status = :status")
        params["status"] = query.status
    if query.begin_time:
        conditions.append("login_time >= :beginTime")
        params["beginTime"] = query.begin_time
    if query.end_time:
        conditions.append("login_time <= :endTime")
        params["endTime"] = query.end_time

    where = " AND ".join(conditions) if conditions else "1=1"

    count_sql = text(f"SELECT COUNT(*) FROM sys_logininfor WHERE {where}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    offset = (query.page_num - 1) * query.page_size
    data_sql = text(f"""
        SELECT info_id, user_name, ipaddr, login_location, browser, os, status, msg, login_time
        FROM sys_logininfor
        WHERE {where}
        ORDER BY login_time DESC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = query.page_size
    params["offset"] = offset
    rows = (await db.execute(data_sql, params)).fetchall()

    result = [
        LoginLogEntity(**r._asdict()).model_dump(by_alias=True, mode="json", exclude_none=True)
        for r in rows
    ]
    return ResponseUtil.paginate(result, total, query.page_num, query.page_size)


@router.get("/loginlog/{info_id}")
async def login_log_detail(
    info_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:list")),
):
    sql = text("SELECT info_id, user_name, ipaddr, login_location, browser, os, status, msg, login_time FROM sys_logininfor WHERE info_id = :id")
    row = (await db.execute(sql, {"id": info_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="日志不存在")
    entity = LoginLogEntity(**row._asdict())
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json", exclude_none=True))


@router.delete("/loginlog/delete/{info_id}")
async def login_log_delete(
    info_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:delete")),
):
    await db.execute(text("DELETE FROM sys_logininfor WHERE info_id = :id"), {"id": info_id})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")


@router.delete("/loginlog/clear")
async def login_log_clear(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:clear")),
):
    await db.execute(text("DELETE FROM sys_logininfor"))
    await db.commit()
    return ResponseUtil.success(msg="已清空")


# ======================== 操作日志 ========================


@router.get("/operlog/list")
async def oper_log_list(
    query: OperLogQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:list")),
):
    conditions: list[str] = []
    params: dict = {}

    if query.title:
        conditions.append("title LIKE :title")
        params["title"] = f"%{query.title}%"
    if query.oper_name:
        conditions.append("oper_name LIKE :operName")
        params["operName"] = f"%{query.oper_name}%"
    if query.status:
        conditions.append("CAST(status AS TEXT) = :status")
        params["status"] = query.status
    if query.begin_time:
        conditions.append("oper_time >= :beginTime")
        params["beginTime"] = query.begin_time
    if query.end_time:
        conditions.append("oper_time <= :endTime")
        params["endTime"] = query.end_time

    where = " AND ".join(conditions) if conditions else "1=1"

    count_sql = text(f"SELECT COUNT(*) FROM sys_oper_log WHERE {where}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    offset = (query.page_num - 1) * query.page_size
    data_sql = text(f"""
        SELECT oper_id, title, business_type, method, request_method, operator_type,
               oper_name, dept_name, oper_url, oper_ip, oper_location,
               oper_param, json_result, status, error_msg, oper_time, cost_time
        FROM sys_oper_log
        WHERE {where}
        ORDER BY oper_time DESC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = query.page_size
    params["offset"] = offset
    rows = (await db.execute(data_sql, params)).fetchall()

    result = [
        OperLogEntity(**r._asdict()).model_dump(by_alias=True, mode="json", exclude_none=True)
        for r in rows
    ]
    return ResponseUtil.paginate(result, total, query.page_num, query.page_size)


@router.get("/operlog/{oper_id}")
async def oper_log_detail(
    oper_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:list")),
):
    sql = text("""
        SELECT oper_id, title, business_type, method, request_method, operator_type,
               oper_name, dept_name, oper_url, oper_ip, oper_location,
               oper_param, json_result, status, error_msg, oper_time, cost_time
        FROM sys_oper_log WHERE oper_id = :id
    """)
    row = (await db.execute(sql, {"id": oper_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="日志不存在")
    entity = OperLogEntity(**row._asdict())
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json", exclude_none=True))


@router.delete("/operlog/delete/{oper_id}")
async def oper_log_delete(
    oper_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:delete")),
):
    await db.execute(text("DELETE FROM sys_oper_log WHERE oper_id = :id"), {"id": oper_id})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")


@router.delete("/operlog/clear")
async def oper_log_clear(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:log:clear")),
):
    await db.execute(text("DELETE FROM sys_oper_log"))
    await db.commit()
    return ResponseUtil.success(msg="已清空")


# ======================== 字典类型 ========================

@router.get("/dict/type/list")
async def dict_type_list(
    query: DictTypeQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:list")),
):
    conditions: list[str] = []
    params: dict = {}

    if query.dict_name:
        conditions.append("dict_name LIKE :dictName")
        params["dictName"] = f"%{query.dict_name}%"
    if query.dict_type:
        conditions.append("dict_type LIKE :dictType")
        params["dictType"] = f"%{query.dict_type}%"
    if query.status:
        conditions.append("status = :status")
        params["status"] = query.status

    where = " AND ".join(conditions) if conditions else "1=1"

    count_sql = text(f"SELECT COUNT(*) FROM sys_dict_type WHERE {where}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    offset = (query.page_num - 1) * query.page_size
    data_sql = text(f"""
        SELECT dict_id, dict_name, dict_type, status, create_time, remark
        FROM sys_dict_type
        WHERE {where}
        ORDER BY dict_id ASC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = query.page_size
    params["offset"] = offset
    rows = (await db.execute(data_sql, params)).fetchall()

    result = [
        DictTypeEntity(**r._asdict()).model_dump(by_alias=True, mode="json", exclude_none=True)
        for r in rows
    ]
    return ResponseUtil.paginate(result, total, query.page_num, query.page_size)


@router.get("/dict/type/{dict_id}")
async def dict_type_detail(
    dict_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:list")),
):
    sql = text("SELECT dict_id, dict_name, dict_type, status, create_time, remark FROM sys_dict_type WHERE dict_id = :id")
    row = (await db.execute(sql, {"id": dict_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="字典类型不存在")
    entity = DictTypeEntity(**row._asdict())
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json"))


@router.post("/dict/type/add")
async def dict_type_add(
    body: DictTypeCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:add")),
):
    check = await db.execute(
        text("SELECT dict_id FROM sys_dict_type WHERE dict_type = :dt"),
        {"dt": body.dict_type},
    )
    if check.fetchone():
        raise HTTPException(status_code=400, detail=f"字典类型「{body.dict_type}」已存在")

    insert_sql = text("""
        INSERT INTO sys_dict_type (dict_name, dict_type, status, create_by, create_time, remark)
        VALUES (:name, :dt, :status, :by, now(), :remark)
        RETURNING dict_id
    """)
    new_id = (await db.execute(insert_sql, {
        "name": body.dict_name, "dt": body.dict_type,
        "status": body.status, "by": user.user_name, "remark": body.remark or "",
    })).scalar_one()
    await db.commit()
    return ResponseUtil.success(msg="新增成功")


@router.put("/dict/type/update")
async def dict_type_update(
    body: DictTypeUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:edit")),
):
    exist = await db.execute(
        text("SELECT dict_id FROM sys_dict_type WHERE dict_id = :id"),
        {"id": body.dict_id},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="字典类型不存在")

    dup = await db.execute(
        text("SELECT dict_id FROM sys_dict_type WHERE dict_type = :dt AND dict_id != :id"),
        {"dt": body.dict_type, "id": body.dict_id},
    )
    if dup.fetchone():
        raise HTTPException(status_code=400, detail=f"字典类型「{body.dict_type}」已存在")

    await db.execute(text("""
        UPDATE sys_dict_type
        SET dict_name = :name, dict_type = :dt, status = :status,
            update_by = :by, update_time = now(), remark = :remark
        WHERE dict_id = :id
    """), {
        "name": body.dict_name, "dt": body.dict_type,
        "status": body.status, "by": user.user_name, "remark": body.remark or "", "id": body.dict_id,
    })
    await db.commit()
    return ResponseUtil.success(msg="更新成功")


@router.delete("/dict/type/delete/{dict_id}")
async def dict_type_delete(
    dict_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:delete")),
):
    exist = await db.execute(
        text("SELECT dict_id, dict_type FROM sys_dict_type WHERE dict_id = :id"),
        {"id": dict_id},
    )
    row = exist.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="字典类型不存在")

    child_count = (await db.execute(
        text("SELECT COUNT(*) FROM sys_dict_data WHERE dict_type = :dt"),
        {"dt": row.dict_type},
    )).scalar() or 0
    if child_count > 0:
        raise HTTPException(status_code=400, detail=f"该字典类型下有 {child_count} 条字典数据，不能删除")

    await db.execute(text("DELETE FROM sys_dict_type WHERE dict_id = :id"), {"id": dict_id})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")


# ======================== 字典数据 ========================

@router.get("/dict/data/list")
async def dict_data_list(
    query: DictDataQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:list")),
):
    conditions: list[str] = []
    params: dict = {}

    if query.dict_type:
        conditions.append("dict_type = :dictType")
        params["dictType"] = query.dict_type
    if query.dict_label:
        conditions.append("dict_label LIKE :dictLabel")
        params["dictLabel"] = f"%{query.dict_label}%"
    if query.status:
        conditions.append("status = :status")
        params["status"] = query.status

    where = " AND ".join(conditions) if conditions else "1=1"

    count_sql = text(f"SELECT COUNT(*) FROM sys_dict_data WHERE {where}")
    total = (await db.execute(count_sql, params)).scalar() or 0

    offset = (query.page_num - 1) * query.page_size
    data_sql = text(f"""
        SELECT dict_code, dict_sort, dict_label, dict_value, dict_type,
               is_default, status, create_time, remark
        FROM sys_dict_data
        WHERE {where}
        ORDER BY dict_sort ASC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = query.page_size
    params["offset"] = offset
    rows = (await db.execute(data_sql, params)).fetchall()

    result = [
        DictDataEntity(**r._asdict()).model_dump(by_alias=True, mode="json", exclude_none=True)
        for r in rows
    ]
    return ResponseUtil.paginate(result, total, query.page_num, query.page_size)


@router.get("/dict/data/{dict_code}")
async def dict_data_detail(
    dict_code: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:list")),
):
    sql = text("""
        SELECT dict_code, dict_sort, dict_label, dict_value, dict_type,
               is_default, status, create_time, remark
        FROM sys_dict_data WHERE dict_code = :code
    """)
    row = (await db.execute(sql, {"code": dict_code})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="字典数据不存在")
    entity = DictDataEntity(**row._asdict())
    return ResponseUtil.success(data=entity.model_dump(by_alias=True, mode="json"))


@router.post("/dict/data/add")
async def dict_data_add(
    body: DictDataCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:add")),
):
    insert_sql = text("""
        INSERT INTO sys_dict_data (dict_sort, dict_label, dict_value, dict_type,
            is_default, status, create_by, create_time, remark)
        VALUES (:sort, :label, :value, :dt, :is_def, :status, :by, now(), :remark)
        RETURNING dict_code
    """)
    new_code = (await db.execute(insert_sql, {
        "sort": body.dict_sort, "label": body.dict_label, "value": body.dict_value,
        "dt": body.dict_type, "is_def": body.is_default,
        "status": body.status, "by": user.user_name, "remark": body.remark or "",
    })).scalar_one()
    await db.commit()
    return ResponseUtil.success(msg="新增成功")


@router.put("/dict/data/update")
async def dict_data_update(
    body: DictDataUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:edit")),
):
    exist = await db.execute(
        text("SELECT dict_code FROM sys_dict_data WHERE dict_code = :code"),
        {"code": body.dict_code},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="字典数据不存在")

    await db.execute(text("""
        UPDATE sys_dict_data
        SET dict_sort = :sort, dict_label = :label, dict_value = :value,
            dict_type = :dt, is_default = :is_def, status = :status,
            update_by = :by, update_time = now(), remark = :remark
        WHERE dict_code = :code
    """), {
        "sort": body.dict_sort, "label": body.dict_label, "value": body.dict_value,
        "dt": body.dict_type, "is_def": body.is_default,
        "status": body.status, "by": user.user_name, "remark": body.remark or "", "code": body.dict_code,
    })
    await db.commit()
    return ResponseUtil.success(msg="更新成功")


@router.delete("/dict/data/delete/{dict_code}")
async def dict_data_delete(
    dict_code: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("system:dict:delete")),
):
    exist = await db.execute(
        text("SELECT dict_code FROM sys_dict_data WHERE dict_code = :code"),
        {"code": dict_code},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="字典数据不存在")

    await db.execute(text("DELETE FROM sys_dict_data WHERE dict_code = :code"), {"code": dict_code})
    await db.commit()
    return ResponseUtil.success(msg="删除成功")
