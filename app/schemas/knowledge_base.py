from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class KnowledgeBaseCreateRequest(BaseModel):
    kb_name: str = Field(description="知识库名称")
    kb_desc: str | None = Field(default=None, description="知识库描述")
    kb_icon: str | None = Field(default=None, description="知识库图标")
    public_flag: str = Field(description="公开状态：0个人 1公开")
    remark: str | None = Field(default=None, description="备注")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)



class KnowledgeBaseEntity(BaseModel):
    kb_id: str | None = None
    kb_name: str | None = None
    kb_desc: str | None = None
    kb_icon: str | None = None
    public_flag: str | None = None
    user_id: str | None = None
    dept_id: str | None = None
    create_by: str | None = None
    create_time: datetime | None = None
    update_by: str | None = None
    update_time: datetime | None = None
    remark: str | None = None
    del_flag: str | None = None
    doc_count: int | None = Field(default=None, description="文档数量")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)
