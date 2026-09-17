"""
语义检索 + 数据权限隔离 + Milvus 混合召回（稠密 + 稀疏向量）

支持两种检索模式：
  - vector_only: 纯向量检索（稠密向量 ANN）
  - hybrid:      稠密向量 + 稀疏向量 混合召回（RRF 融合）
"""

import httpx
from pymilvus import AnnSearchRequest, RRFRanker

from app.config.config import settings
from app.core.get_milvus import MilvusClient

_RRF_K = 60


async def _vector_search(query: str, dept_id: int | None, top_k: int) -> list[dict]:
    """纯稠密向量检索"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.embedding_url}/embed",
            json={"text": query},
        )
        resp.raise_for_status()
        vector = resp.json()["vector"]

    milvus_client = MilvusClient.get_client()
    expr = f'dept_id == "{dept_id}"' if dept_id is not None else None
    results = milvus_client.search(
        collection_name=settings.milvus_collection,
        data=[vector],
        limit=top_k,
        output_fields=["content", "doc_id", "filename", "chunk_index", "kb_id", "dept_id"],
        search_params={"metric_type": "COSINE"},
        filter=expr,
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "id": hit["id"],# 返回的是这个分块的 chunk_id，类似chunk_9f3a2b1c
            "score": hit["distance"],
            **hit["entity"],#** 用在字典前面，表示"把这个字典拆开，把所有键值对摊平放进当前字典"
        })
    return hits


async def _hybrid_search(query: str, dept_id: int | None, top_k: int) -> list[dict]:
    """稠密 + 稀疏向量混合检索（RRF 融合）"""
    # 1. 获取查询的稠密 + 稀疏向量
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.embedding_url}/embed/sparse",
            json={"texts": [query]},
        )
        resp.raise_for_status()
        data = resp.json()
    dense_vec = data["dense_vectors"][0]
    sparse_vec = data["sparse_vectors"][0]

    milvus_client = MilvusClient.get_client()
    expr = f'dept_id == "{dept_id}"' if dept_id is not None else None

    # 2. 稠密向量 ANN 请求
    dense_req = AnnSearchRequest(
        data=[dense_vec],
        anns_field="vector",
        param={"metric_type": "COSINE"},
        limit=top_k,
        expr=expr,
    )

    # 3. 稀疏向量 ANN 请求
    sparse_req = AnnSearchRequest(
        data=[sparse_vec],
        anns_field="sparse_vector",
        param={"metric_type": "IP"},
        limit=top_k,
        expr=expr,
    )

    # 4. 混合检索 + RRF 融合
    results = milvus_client.hybrid_search(
        collection_name=settings.milvus_collection,
        reqs=[dense_req, sparse_req],
        ranker=RRFRanker(k=_RRF_K),  # RRF融合
        limit=top_k,
        output_fields=["content", "doc_id", "filename", "chunk_index", "kb_id", "dept_id"],
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "id": hit["id"],
            "score": hit["distance"],
            **hit["entity"],
        })
    return hits


async def rag_research(
    query: str,
    dept_id: int | None = None,
    top_k: int = 5,
    mode: str = "hybrid",
) -> list[dict]:
    if mode == "vector_only":
        return await _vector_search(query, dept_id, top_k)
    else:
        return await _hybrid_search(query, dept_id, top_k)
