import asyncio
from typing import Optional, List

import httpx

from app.config.config import settings

BATCH_SIZE = 16

"""调用 BGE-M3 服务批量获取稠密向量"""
async def embed_texts(texts: list[str]) -> Optional[List[List[float]]]:
    # 如果文本为空，则返回空列表
    if not texts:
        return []

    #这段代码不是在本项目里做向量化，而是通过 HTTP 请求调用另一个独立的向量化服务（BGE-M3 嵌入服务）。
    # 异步客户端是 httpx.AsyncClient。
    """
    把文本发给另一个服务去向量化，那个服务就是之前你问过的 bge_server.py（BGE-M3 嵌入服务）。
    你的项目（rag-backend）
    │
    │ 1. 把文本批量 POST 到 http://127.0.0.1:9003/embed/batch
    ▼
    BGE-M3 嵌入服务（emb-server，另一个进程）
    │
    │ 2. 用 BGE-M3 模型把文本转成 1024 维向量
    ▼
    返回 {"vectors": [[0.23, -0.45, ...], ...]}
    │
    │ 3. 你的项目拿到向量
    ▼
    存进 Milvus
    """
    async with httpx.AsyncClient(timeout=120) as client:
        all_vectors = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            resp = await client.post(
                f"{settings.embedding_url}/embed/batch",#请求地址
                json={"texts": batch},#发送一批文本
            )
            # 检查响应，非200状态码直接抛出异常
            resp.raise_for_status()
            # 把返回的向量添加到结果列表中
            all_vectors.extend(resp.json()["vectors"])
        return all_vectors

"""
调用 BGE-M3 服务批量获取稠密 + 稀疏向量
"""
async def embed_texts_hybrid(texts: list[str]) -> tuple[list[list[float]], list[dict]]:
    """
    调用 BGE-M3 服务批量获取稠密 + 稀疏向量
    Returns:
        (dense_vectors, sparse_vectors)
        - dense_vectors: list[list[float]]  稠密向量
        - sparse_vectors: list[dict[int, float]]  稀疏向量 {token_id: weight}
    """
    if not texts:
        return [], []
    async with httpx.AsyncClient(timeout=120) as client:
        all_dense = []
        all_sparse = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            resp = await client.post(
                f"{settings.embedding_url}/embed/sparse",
                json={"texts": batch},
            )
            resp.raise_for_status()
            data = resp.json()
            all_dense.extend(data["dense_vectors"])
            all_sparse.extend(data["sparse_vectors"])
        return all_dense, all_sparse
