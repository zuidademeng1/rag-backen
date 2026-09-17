from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DocumentEntity(BaseModel):
    doc_id: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    file_path: str | None = None
    file_ext: str | None = None
    kb_id: str | None = None
    chunk_status: str | None = None
    upload_by: str | None = None
    uploader_id: int | None = None
    upload_time: datetime | None = None
    dept_id: int | None = None
    update_time: datetime | None = None
    remark: str | None = None
    del_flag: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)
