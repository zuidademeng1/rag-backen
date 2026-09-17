from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


class ResponseModel(BaseModel):
    code: int = 0
    msg: str = "操作成功"
    data: Any = None


# 分页数据
class PageData(BaseModel):
    rows: list = []
    total: int = 0
    page_num: int = 1
    page_size: int = 10


class ResponseUtil:

    @staticmethod
    def success(data: Any = None, msg: str = "操作成功") -> ResponseModel:
        if isinstance(data, BaseModel):
            data = data.model_dump(by_alias=True, mode="json")
        return ResponseModel(code=0, msg=msg, data=data)

    @staticmethod
    def error(msg: str = "操作失败", code: int = 1) -> ResponseModel:
        return ResponseModel(code=code, msg=msg, data=None)

    @staticmethod
    def paginate(rows: list, total: int, page_num: int, page_size: int, msg: str = "查询成功") -> ResponseModel:
        data = PageData(rows=rows, total=total, page_num=page_num, page_size=page_size)
        return ResponseModel(code=0, msg=msg, data=data.model_dump(by_alias=True, mode="json"))

    @staticmethod
    async def paginate_query(
        db: AsyncSession,
        query_fn: Callable,
        entity_class: type[BaseModel],
        page_num: int = 1,
        page_size: int = 10,
        **filters,
    ) -> ResponseModel:
        """通用分页查询：ORM 分页 → 转 Entity → 驼峰序列化（query_fn 可以是 Service/DAO 方法）"""
        items, total = await query_fn(db, page_num=page_num, page_size=page_size, **filters)
        rows = [
            entity_class.model_validate(item).model_dump(by_alias=True, mode="json")
            for item in items
        ]
        return ResponseUtil.paginate(rows=rows, total=total, page_num=page_num, page_size=page_size)
