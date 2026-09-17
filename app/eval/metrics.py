"""检索评估指标（纯函数，不依赖外部服务）。

约定：retrieved 和 relevant 都是分块集合，元素为 (doc_id, chunk_index) 元组。
"""


def _chunk_set(chunks: list[dict]) -> set[tuple]:
    """把分块标注列表转成 {(doc_id, chunk_index)} 集合。"""
    return {(c["doc_id"], c["chunk_index"]) for c in chunks}


def hit_rate(retrieved: list[tuple], relevant: set[tuple]) -> bool:
    """top_k 结果是否命中至少一个相关分块（1 或 0）。"""
    return bool(set(retrieved) & relevant)


def recall(retrieved: list[tuple], relevant: set[tuple]) -> float:
    """召回率：命中的相关分块数 / 总相关分块数。"""
    if not relevant:
        return 0.0
    return len(set(retrieved) & relevant) / len(relevant)


def precision(retrieved: list[tuple], relevant: set[tuple]) -> float:
    """精确率：命中的相关分块数 / 检索返回的分块数。"""
    if not retrieved:
        return 0.0
    return len(set(retrieved) & relevant) / len(retrieved)


def mrr(retrieved: list[tuple], relevant: set[tuple]) -> float:
    """MRR：第一个相关分块排名的倒数（排名从 1 开始）。"""
    for i, chunk in enumerate(retrieved, start=1):
        if chunk in relevant:
            return 1.0 / i
    return 0.0
