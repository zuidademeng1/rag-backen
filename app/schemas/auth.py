from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class LoginRequest(BaseModel):
    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class UserInfo(BaseModel):
    user_id: int
    user_name: str
    nick_name: str
    dept_id: int | None = None
    dept_name: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class LoginResponse(BaseModel):
    token: str
    user: UserInfo

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class RouteMeta(BaseModel):
    title: str = ""
    icon: str = ""
    menu_type: str = ""  # M-目录 C-菜单 F-按钮
    perms: str = ""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class RouteItem(BaseModel):
    path: str
    component: str | None = None
    name: str = ""
    meta: RouteMeta = Field(default_factory=RouteMeta)
    children: list["RouteItem"] = Field(default_factory=list)
    redirect: str | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
