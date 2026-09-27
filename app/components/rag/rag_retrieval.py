"""
语义检索 + Milvus 混合召回（稠密 + 稀疏向量）

支持两种检索模式：
  - vector_only: 纯向量检索（稠密向量 ANN）
  - hybrid:      稠密 + 稀疏 混合召回，RRF 融合在 Python 侧完成
                 （规避 Milvus hybrid_search 的 RRF ranker 对 VARCHAR 主键不兼容的问题）

过滤：按 kb_id IN(...) 过滤；kb_ids 为空则不过滤（全校公共库）。
"""

import httpx

from app.config.config import settings
from app.core.get_milvus import MilvusClient

_RRF_K = 60

_OUTPUT_FIELDS = ["content", "doc_id", "filename", "chunk_index", "kb_id", "dept_id"]


def _build_kb_expr(kb_ids) -> str | None:
    """构建 kb_id 过滤表达式；kb_ids 为空/None 时返回 None（不过滤）"""
    if not kb_ids:
        return None
    quoted = ", ".join(f'"{kb}"' for kb in kb_ids)
    return f'kb_id in [{quoted}]'


async def _vector_search(query: str, kb_ids: list[str] | None, top_k: int) -> list[dict]:
    """纯稠密向量检索"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{settings.embedding_url}/embed", json={"text": query})
        resp.raise_for_status()
        vector = resp.json()["vector"]

    milvus_client = MilvusClient.get_client()
    results = milvus_client.search(
        collection_name=settings.milvus_collection,
        data=[vector],
        limit=top_k,
        output_fields=_OUTPUT_FIELDS,
        search_params={"metric_type": "COSINE"},
        filter=_build_kb_expr(kb_ids),
    )

    hits = []
    for hit in results[0]:
        hits.append({"id": hit["id"], "score": hit["distance"], **hit["entity"]})
    return hits


async def _hybrid_search(query: str, kb_ids: list[str] | None, top_k: int) -> list[dict]:
    """稠密 + 稀疏向量混合检索（RRF 融合，Python 侧完成）"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.embedding_url}/embed/sparse", json={"texts": [query]}
        )
        resp.raise_for_status()
        data = resp.json()
    dense_vec = data["dense_vectors"][0]
    sparse_vec = data["sparse_vectors"][0]

    milvus_client = MilvusClient.get_client()
    expr = _build_kb_expr(kb_ids)

    # 1. 稠密向量 ANN 检索
    dense_results = milvus_client.search(
        collection_name=settings.milvus_collection,
        data=[dense_vec],
        anns_field="vector",
        limit=top_k,
        output_fields=_OUTPUT_FIELDS,
        search_params={"metric_type": "COSINE"},
        filter=expr,
    )
    # 2. 稀疏向量 ANN 检索
    sparse_results = milvus_client.search(
        collection_name=settings.milvus_collection,
        data=[sparse_vec],
        anns_field="sparse_vector",
        limit=top_k,
        output_fields=_OUTPUT_FIELDS,
        search_params={"metric_type": "IP"},
        filter=expr,
    )

    # 3. RRF 融合：score = Σ 1/(k + rank)
    rrf_scores: dict[str, float] = {}
    hit_map: dict[str, dict] = {}
    for result_list in (dense_results[0], sparse_results[0]):
        for rank, hit in enumerate(result_list):
            key = hit["id"]
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
            if key not in hit_map:
                hit_map[key] = {**hit["entity"], "id": hit["id"]}

    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:top_k]
    hits = [dict(hit_map[k], score=rrf_scores[k]) for k in sorted_keys]
    return hits


async def rag_research(
    query: str,
    kb_ids: list[str] | None = None,
    top_k: int = 5,
    mode: str = "hybrid",
) -> list[dict]:
    if mode == "vector_only":
        return await _vector_search(query, kb_ids, top_k)
    return await _hybrid_search(query, kb_ids, top_k)
