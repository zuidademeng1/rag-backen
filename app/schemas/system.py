from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# ========== 用户管理 ==========

class UserQuery(CamelModel):
    page_num: int = Field(default=1, alias="pageNum")
    page_size: int = Field(default=10, alias="pageSize")
    user_name: Optional[str] = Field(default=None, alias="userName")
    status: Optional[str] = None
    dept_id: Optional[int] = Field(default=None, alias="deptId")


class UserCreate(CamelModel):
    user_name: str = Field(alias="userName")
    nick_name: str = Field(alias="nickName")
    password: str = "123456"
    dept_id: Optional[int] = Field(default=None, alias="deptId")
    email: Optional[str] = None
    phone: Optional[str] = None
    sex: Optional[str] = "0"
    status: str = "0"
    role_ids: list[int] = Field(default=[], alias="roleIds")


class UserUpdate(CamelModel):
    user_id: int = Field(alias="userId")
    user_name: str = Field(alias="userName")
    nick_name: str = Field(alias="nickName")
    password: Optional[str] = None
    dept_id: Optional[int] = Field(default=None, alias="deptId")
    email: Optional[str] = None
    phone: Optional[str] = None
    sex: Optional[str] = "0"
    status: str = "0"
    role_ids: list[int] = Field(default=[], alias="roleIds")


class UserEntity(CamelModel):
    user_id: int = Field(alias="userId")
    user_name: str = Field(alias="userName")
    nick_name: str = Field(alias="nickName")
    dept_id: Optional[int] = Field(default=None, alias="deptId")
    dept_name: Optional[str] = Field(default=None, alias="deptName")
    email: Optional[str] = None
    phone: Optional[str] = None
    sex: Optional[str] = "0"
    status: str = "0"
    create_time: Optional[datetime] = Field(default=None, alias="createTime")
    role_ids: list[int] = Field(default=[], alias="roleIds")


class ResetPwd(CamelModel):
    user_id: int = Field(alias="userId")
    password: str = "123456"


class AuthRoleBody(CamelModel):
    user_id: int = Field(alias="userId")
    role_ids: list[int] = Field(alias="roleIds")


# ========== 角色管理 ==========

class RoleQuery(CamelModel):
    page_num: int = Field(default=1, alias="pageNum")
    page_size: int = Field(default=10, alias="pageSize")
    role_name: Optional[str] = Field(default=None, alias="roleName")
    status: Optional[str] = None


class RoleCreate(CamelModel):
    role_name: str = Field(alias="roleName")
    role_key: str = Field(alias="roleKey")
    role_sort: int = Field(default=0, alias="roleSort")
    status: str = "0"
    menu_ids: list[int] = Field(default=[], alias="menuIds")


class RoleUpdate(CamelModel):
    role_id: int = Field(alias="roleId")
    role_name: str = Field(alias="roleName")
    role_key: str = Field(alias="roleKey")
    role_sort: int = Field(default=0, alias="roleSort")
    status: str = "0"
    menu_ids: list[int] = Field(default=[], alias="menuIds")


class RoleEntity(CamelModel):
    role_id: int = Field(alias="roleId")
    role_name: str = Field(alias="roleName")
    role_key: str = Field(alias="roleKey")
    role_sort: int = Field(default=0, alias="roleSort")
    status: str = "0"
    create_time: Optional[datetime] = Field(default=None, alias="createTime")


class MenuTreeBody(CamelModel):
    role_id: int = Field(alias="roleId")
    menu_ids: list[int] = Field(alias="menuIds")


# ========== 菜单管理 ==========

class MenuQuery(CamelModel):
    menu_name: Optional[str] = Field(default=None, alias="menuName")
    status: Optional[str] = None


class MenuCreate(CamelModel):
    menu_name: str = Field(alias="menuName")
    parent_id: int = Field(default=0, alias="parentId")
    order_num: int = Field(default=0, alias="orderNum")
    path: Optional[str] = ""
    component: Optional[str] = None
    route_name: Optional[str] = Field(default=None, alias="routeName")
    menu_type: str = Field(default="", alias="menuType")
    visible: str = "0"
    status: str = "0"
    perms: Optional[str] = None
    icon: Optional[str] = "#"
    is_frame: str | int = Field(default="1", alias="isFrame")
    is_cache: str | int = Field(default="0", alias="isCache")


class MenuUpdate(CamelModel):
    menu_id: int = Field(alias="menuId")
    menu_name: str = Field(alias="menuName")
    parent_id: int = Field(default=0, alias="parentId")
    order_num: int = Field(default=0, alias="orderNum")
    path: Optional[str] = ""
    component: Optional[str] = None
    route_name: Optional[str] = Field(default=None, alias="routeName")
    menu_type: str = Field(default="", alias="menuType")
    visible: str = "0"
    status: str = "0"
    perms: Optional[str] = None
    icon: Optional[str] = "#"
    is_frame: str | int = Field(default="1", alias="isFrame")
    is_cache: str | int = Field(default="0", alias="isCache")


class MenuEntity(CamelModel):
    menu_id: int = Field(alias="menuId")
    menu_name: str = Field(alias="menuName")
    parent_id: int = Field(default=0, alias="parentId")
    order_num: int = Field(default=0, alias="orderNum")
    path: Optional[str] = ""
    component: Optional[str] = None
    route_name: Optional[str] = Field(default=None, alias="routeName")
    menu_type: str = Field(default="", alias="menuType")
    visible: str = "0"
    status: str = "0"
    perms: Optional[str] = None
    icon: Optional[str] = "#"
    is_frame: str | int = Field(default="1", alias="isFrame")
    is_cache: str | int = Field(default="0", alias="isCache")
    children: list["MenuEntity"] = Field(default=[])


class MenuTreeItem(CamelModel):
    id: int
    label: str
    children: list["MenuTreeItem"] = Field(default=[])


# ========== 部门管理 ==========

class DeptQuery(CamelModel):
    dept_name: Optional[str] = Field(default=None, alias="deptName")
    status: Optional[str] = None


class DeptCreate(CamelModel):
    dept_name: str = Field(alias="deptName")
    parent_id: int = Field(default=0, alias="parentId")
    order_num: int = Field(default=0, alias="orderNum")
    leader: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = "0"


class DeptUpdate(CamelModel):
    dept_id: int = Field(alias="deptId")
    dept_name: str = Field(alias="deptName")
    parent_id: int = Field(default=0, alias="parentId")
    order_num: int = Field(default=0, alias="orderNum")
    leader: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = "0"


class DeptEntity(CamelModel):
    dept_id: int = Field(alias="deptId")
    parent_id: int = Field(default=0, alias="parentId")
    dept_name: str = Field(alias="deptName")
    order_num: int = Field(default=0, alias="orderNum")
    leader: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = "0"
    create_time: Optional[datetime] = Field(default=None, alias="createTime")
    children: list["DeptEntity"] = Field(default=[])


# ========== 登录日志 ==========

class LoginLogQuery(CamelModel):
    page_num: int = Field(default=1, alias="pageNum")
    page_size: int = Field(default=10, alias="pageSize")
    user_name: Optional[str] = Field(default=None, alias="userName")
    status: Optional[str] = None
    begin_time: Optional[str] = Field(default=None, alias="beginTime")
    end_time: Optional[str] = Field(default=None, alias="endTime")


class LoginLogEntity(CamelModel):
    info_id: int = Field(alias="infoId")
    user_name: Optional[str] = Field(default=None, alias="userName")
    ipaddr: Optional[str] = None
    login_location: Optional[str] = Field(default=None, alias="loginLocation")
    browser: Optional[str] = None
    os: Optional[str] = None
    status: Optional[str] = "0"
    msg: Optional[str] = None
    login_time: Optional[datetime] = Field(default=None, alias="loginTime")


# ========== 操作日志 ==========

class OperLogQuery(CamelModel):
    page_num: int = Field(default=1, alias="pageNum")
    page_size: int = Field(default=10, alias="pageSize")
    title: Optional[str] = None
    oper_name: Optional[str] = Field(default=None, alias="operName")
    status: Optional[str] = None
    begin_time: Optional[str] = Field(default=None, alias="beginTime")
    end_time: Optional[str] = Field(default=None, alias="endTime")


class OperLogEntity(CamelModel):
    oper_id: int = Field(alias="operId")
    title: Optional[str] = None
    business_type: int = Field(default=0, alias="businessType")
    method: Optional[str] = None
    request_method: Optional[str] = Field(default=None, alias="requestMethod")
    operator_type: int = Field(default=0, alias="operatorType")
    oper_name: Optional[str] = Field(default=None, alias="operName")
    dept_name: Optional[str] = Field(default=None, alias="deptName")
    oper_url: Optional[str] = Field(default=None, alias="operUrl")
    oper_ip: Optional[str] = Field(default=None, alias="operIp")
    oper_location: Optional[str] = Field(default=None, alias="operLocation")
    oper_param: Optional[str] = Field(default=None, alias="operParam")
    json_result: Optional[str] = Field(default=None, alias="jsonResult")
    status: int = 0
    error_msg: Optional[str] = Field(default=None, alias="errorMsg")
    oper_time: Optional[datetime] = Field(default=None, alias="operTime")
    cost_time: int = Field(default=0, alias="costTime")


# ========== 字典类型 ==========

class DictTypeQuery(CamelModel):
    page_num: int = Field(default=1, alias="pageNum")
    page_size: int = Field(default=10, alias="pageSize")
    dict_name: Optional[str] = Field(default=None, alias="dictName")
    dict_type: Optional[str] = Field(default=None, alias="dictType")
    status: Optional[str] = None


class DictTypeCreate(CamelModel):
    dict_name: str = Field(alias="dictName")
    dict_type: str = Field(alias="dictType")
    status: str = "0"
    remark: Optional[str] = None


class DictTypeUpdate(CamelModel):
    dict_id: int = Field(alias="dictId")
    dict_name: str = Field(alias="dictName")
    dict_type: str = Field(alias="dictType")
    status: str = "0"
    remark: Optional[str] = None


class DictTypeEntity(CamelModel):
    dict_id: int = Field(alias="dictId")
    dict_name: str = Field(alias="dictName")
    dict_type: str = Field(alias="dictType")
    status: str = "0"
    create_time: Optional[datetime] = Field(default=None, alias="createTime")
    remark: Optional[str] = None


# ========== 字典数据 ==========

class DictDataQuery(CamelModel):
    page_num: int = Field(default=1, alias="pageNum")
    page_size: int = Field(default=10, alias="pageSize")
    dict_type: Optional[str] = Field(default=None, alias="dictType")
    dict_label: Optional[str] = Field(default=None, alias="dictLabel")
    status: Optional[str] = None


class DictDataCreate(CamelModel):
    dict_sort: int = Field(default=0, alias="dictSort")
    dict_label: str = Field(alias="dictLabel")
    dict_value: str = Field(alias="dictValue")
    dict_type: str = Field(alias="dictType")
    is_default: str = Field(default="N", alias="isDefault")
    status: str = "0"
    remark: Optional[str] = None


class DictDataUpdate(CamelModel):
    dict_code: int = Field(alias="dictCode")
    dict_sort: int = Field(default=0, alias="dictSort")
    dict_label: str = Field(alias="dictLabel")
    dict_value: str = Field(alias="dictValue")
    dict_type: str = Field(alias="dictType")
    is_default: str = Field(default="N", alias="isDefault")
    status: str = "0"
    remark: Optional[str] = None


class DictDataEntity(CamelModel):
    dict_code: int = Field(alias="dictCode")
    dict_sort: int = Field(default=0, alias="dictSort")
    dict_label: str = Field(alias="dictLabel")
    dict_value: str = Field(alias="dictValue")
    dict_type: str = Field(alias="dictType")
    is_default: str = Field(default="N", alias="isDefault")
    status: str = "0"
    create_time: Optional[datetime] = Field(default=None, alias="createTime")
    remark: Optional[str] = None
