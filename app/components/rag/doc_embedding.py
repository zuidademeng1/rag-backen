import asyncio
from typing import Optional, List

import httpx

from app.config.config import settings

BATCH_SIZE = 16

# 可重试的瞬时错误状态码（网关超时 / 服务暂不可用等）
_RETRIABLE_STATUS = {502, 503, 504}
_MAX_RETRIES = 3


async def _post_embed(client: httpx.AsyncClient, url: str, body: dict) -> dict:
    """带重试的嵌入请求：对 502/503/504 退避重试，其余异常直接抛出"""
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in _RETRIABLE_STATUS and attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise


"""调用 BGE-M3 服务批量获取稠密向量"""
async def embed_texts(texts: list[str]) -> Optional[List[List[float]]]:
    # 如果文本为空，则返回空列表
    if not texts:
        return []

    async with httpx.AsyncClient(timeout=120) as client:
        all_vectors = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            data = await _post_embed(
                client,
                f"{settings.embedding_url}/embed/batch",
                {"texts": batch},
            )
            all_vectors.extend(data["vectors"])
        return all_vectors


"""调用 BGE-M3 服务批量获取稠密 + 稀疏向量"""
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
            data = await _post_embed(
                client,
                f"{settings.embedding_url}/embed/sparse",
                {"texts": batch},
            )
            all_dense.extend(data["dense_vectors"])
            all_sparse.extend(data["sparse_vectors"])
        return all_dense, all_sparse
