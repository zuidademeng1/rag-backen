from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ==================== 会话 ====================

class SessionCreateRequest(BaseModel):
    title: str = Field(default="", description="会话标题")
    remark: str | None = Field(default=None, description="备注")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)


class SessionUpdateRequest(BaseModel):
    session_id: str = Field(description="会话ID")
    title: str | None = Field(default=None, description="会话标题")
    status: str | None = Field(default=None, description="状态：active-活跃，archived-归档")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)


class SessionEntity(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    title: str | None = None
    status: str | None = None
    dept_id: str | None = None
    create_by: str | None = None
    create_time: datetime | None = None
    update_by: str | None = None
    update_time: datetime | None = None
    remark: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)


# ==================== 会话记录 ====================

class RecordAddRequest(BaseModel):
    session_id: str = Field(description="会话ID")
    role: str = Field(description="角色：user-用户，assistant-AI助手")
    content: str = Field(description="消息内容")
    token_count: int = Field(default=0, description="token估算值")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)


class RecordEntity(BaseModel):
    record_id: str | None = None
    session_id: str | None = None
    role: str | None = None
    content: str | None = None
    msg_index: int | None = None
    token_count: int | None = None
    create_time: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)
