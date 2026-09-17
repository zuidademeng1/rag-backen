"""
重新创建 Milvus 集合：新增 sparse_vector 字段，用于混合检索（稠密+稀疏）。

警告：会删除原有集合中的所有数据！
"""

from pymilvus import MilvusClient, DataType
from pymilvus.milvus_client.index import IndexParams

from app.config.config import settings


def recreate():
    client = MilvusClient(
        uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
        timeout=settings.milvus_timeout,
    )

    collection_name = settings.milvus_collection

    # 删除已存在的集合
    if client.has_collection(collection_name):
        print(f"删除已有集合: {collection_name}")
        client.drop_collection(collection_name)

    # 创建 schema
    schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=False,
    )
    schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=64, is_primary=True)
    schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="kb_id", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="filename", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
    schema.add_field(field_name="dept_id", datatype=DataType.VARCHAR, max_length=256, nullable=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=settings.milvus_dimension)
    schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
    )
    print(f"集合创建成功: {collection_name}")

    # 稠密向量索引
    dense_idx = IndexParams()
    dense_idx.add_index(
        field_name="vector",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )
    client.create_index(collection_name=collection_name, index_params=dense_idx)
    print("稠密向量索引创建成功 (vector / COSINE / AUTOINDEX)")

    # 稀疏向量索引
    sparse_idx = IndexParams()
    sparse_idx.add_index(
        field_name="sparse_vector",
        index_type="SPARSE_INVERTED_INDEX",
        metric_type="IP",
    )
    client.create_index(collection_name=collection_name, index_params=sparse_idx)
    print("稀疏向量索引创建成功 (sparse_vector / IP / SPARSE_INVERTED_INDEX)")

    # 加载集合到内存（搜索前必须）
    client.load_collection(collection_name)
    print("集合已加载到内存")

    # 验证
    desc = client.describe_collection(collection_name)
    fields = [(f["name"], str(f["type"])) for f in desc["fields"]]
    print(f"\n最终 schema: {fields}")

    indexes = client.list_indexes(collection_name)
    print(f"索引: {indexes}")
    print("Done!")


if __name__ == "__main__":
    recreate()
