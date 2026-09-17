from sqlalchemy import text

from app.utils.auth_util import CurrentUser


def build_data_scope_sql(
    db_table_alias: str,
    user: CurrentUser,
    dept_id_field: str | None = None,
    user_id_field: str | None = None,
) -> str:
    """根据用户的数据权限范围生成 SQL WHERE 条件片段

    Args:
        db_table_alias: 表别名，如 "kb" / "d"
        user: 当前用户
        dept_id_field: 部门 ID 字段名，默认 {alias}.dept_id
        user_id_field: 用户 ID 字段名，默认 {alias}.user_id

    RuoYi data_scope 取值:
        "1" — 全部数据权限
        "2" — 自定义数据权限（通过 sys_role_dept 查）
        "3" — 本部门数据权限
        "4" — 本部门及以下数据权限
        "5" — 仅本人数据权限
    """
    if user.is_admin or user.data_scope == "1":
        return ""

    dept_id_field = dept_id_field or f"{db_table_alias}.dept_id"
    user_id_field = user_id_field or f"{db_table_alias}.user_id"

    if user.data_scope == "5":
        return f"AND {user_id_field} = {user.user_id}"

    if user.data_scope == "3":
        if user.dept_id:
            return f"AND {dept_id_field} = {user.dept_id}"
        return f"AND {user_id_field} = {user.user_id}"

    if user.data_scope == "4":
        if user.dept_id:
            return (
                f"AND ({dept_id_field} = {user.dept_id} "
                f"OR {dept_id_field} IN ("
                f"  SELECT dept_id FROM sys_dept "
                f"  WHERE ancestors LIKE '%/{user.dept_id}/%' OR dept_id = {user.dept_id}"
                f"  AND del_flag = '0'"
                f"))"
            )
        return f"AND {user_id_field} = {user.user_id}"

    if user.data_scope == "2":
        return (
            f"AND {dept_id_field} IN ("
            f"  SELECT rd.dept_id FROM sys_role_dept rd"
            f"  JOIN sys_user_role ur ON rd.role_id = ur.role_id"
            f"  WHERE ur.user_id = {user.user_id}"
            f")"
        )

    return ""


def apply_data_scope_to_query(
    query: str,
    db_table_alias: str,
    user: CurrentUser,
    dept_id_field: str | None = None,
    user_id_field: str | None = None,
) -> str:
    """将数据权限 SQL 片段附加到已有查询的 WHERE 子句末尾"""
    clause = build_data_scope_sql(db_table_alias, user, dept_id_field, user_id_field)
    if not clause:
        return query
    return query.replace("/* data_scope */", clause)
