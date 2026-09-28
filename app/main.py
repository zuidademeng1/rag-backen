import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.doc import router as doc_router
from app.api.knowledge_base import router as kb_router
from app.api.session import router as session_router
from app.api.chat import router as chat_router
from app.api.system import router as system_router
from app.config.config import settings
from app.core.database import async_engine
from app.core.exception_handler import (
    ServiceException,
    global_exception_handler,
    http_exception_handler,
    service_exception_handler,
    validation_exception_handler,
)
from app.core.get_milvus import MilvusClient
from app.core.get_redis import RedisClient
from app.services.task_worker import start_worker, stop_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 连接 Milvus
    await MilvusClient.connect()
    milvus_client = MilvusClient.get_client()

    # 检查集合是否存在，不存在则创建
    if not milvus_client.has_collection(settings.milvus_collection):
        _create_milvus_collection(milvus_client)

    # 加载集合到内存（搜索前必须加载）
    milvus_client.load_collection(settings.milvus_collection)

    # 启动后台 worker
    worker_task = asyncio.create_task(start_worker())
    yield
    # 关闭后台 worker 和连接
    await stop_worker()
    worker_task.cancel()
    await RedisClient.close()
    await MilvusClient.close()
    await async_engine.dispose()


def _create_milvus_collection(client):
    """创建 Milvus 集合（稠密向量 + 稀疏向量，支持混合检索）"""
    from pymilvus import DataType
    from pymilvus.milvus_client.index import IndexParams

    collection_name = settings.milvus_collection

# collection 就是 Milvus 里的「表」，是存储向量数据的容器。schema 是这张表的结构定义，规定表里有哪些字段、每个字段什么类型。
# 类比关系数据库：
# Milvus	关系数据库（如 MySQL）
# collection	表（table）
# field	列（column）
# schema	建表语句（CREATE TABLE ...）
# entity	行（row）

    schema = client.create_schema(
        auto_id=False,
        enable_dynamic_field=False,
    )
    schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=64, is_primary=True)
    schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="kb_id", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="filename", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
    schema.add_field(field_name="section", datatype=DataType.VARCHAR, max_length=256, nullable=True)
    schema.add_field(field_name="effective_date", datatype=DataType.VARCHAR, max_length=64, nullable=True)
    schema.add_field(field_name="dept_id", datatype=DataType.VARCHAR, max_length=256, nullable=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=settings.milvus_dimension)
    schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

    client.create_collection(collection_name=collection_name, schema=schema)
#先定义 schema，再 create_collection — 就像先写建表语句，再真正建表
# 前面的schema翻译成SQL语句大概是：
# CREATE TABLE ai_embeddings (
#     id           VARCHAR(64) PRIMARY KEY,
#     content      VARCHAR(65535),
#     vector       FLOAT_VECTOR(1024),     -- 1024维稠密向量
#     sparse_vector SPARSE_FLOAT_VECTOR     -- 稀疏向量
# );
    # 稠密向量索引
    dense_idx = IndexParams()
    dense_idx.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
    client.create_index(collection_name=collection_name, index_params=dense_idx)

    # 稀疏向量索引
    sparse_idx = IndexParams()
    sparse_idx.add_index(field_name="sparse_vector", index_type="SPARSE_INVERTED_INDEX", metric_type="IP")
    client.create_index(collection_name=collection_name, index_params=sparse_idx)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ServiceException, service_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth_router)
app.include_router(doc_router)
app.include_router(kb_router)
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(system_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#健康检查接口
@app.get("/dev-api/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


if __name__ == '__main__':

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port, reload=settings.app_reload,
                log_level=settings.log_level)
