from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DocumentChunkEntity(BaseModel):
    chunk_id: str | None = None
    doc_id: str | None = None
    chunk_index: int | None = None
    content: str | None = None
    char_count: int | None = None
    dept_id: str | None = None
    create_time: datetime | None = None
    update_time: datetime | None = None
    remark: str | None = None
    del_flag: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)
