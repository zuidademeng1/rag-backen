"""检索层评估：纯检索效果，不经过 LLM 生成。

对每条黄金数据调用 rag_research 检索 top_k 分块，计算
hit_rate / recall / precision / mrr，并汇总平均分。
"""

from app.components.rag.rag_retrieval import rag_research
from app.eval import metrics
from app.eval.golden_data import GOLDEN_DATA


async def evaluate_retrieval(top_k: int = 5, mode: str = "hybrid") -> dict:
    """检索层评估。

    Args:
        top_k: 检索返回的分块数
        mode: 检索模式，hybrid（混合）或 vector_only（纯稠密）

    Returns:
        汇总报告 dict，含每个 query 的明细和整体平均分
    """
    per_query = []
    hit_sum = 0.0
    recall_sum = 0.0
    precision_sum = 0.0
    mrr_sum = 0.0

    for item in GOLDEN_DATA:
        query = item["query"]
        relevant = metrics._chunk_set(item["relevant_chunks"])

        results = await rag_research(query=query, top_k=top_k, mode=mode)
        # 检索结果转成 (doc_id, chunk_index) 集合，保持顺序（mrr 依赖顺序）
        retrieved = [(r.get("doc_id"), r.get("chunk_index")) for r in results]

        h = metrics.hit_rate(retrieved, relevant)
        r = metrics.recall(retrieved, relevant)
        p = metrics.precision(retrieved, relevant)
        m = metrics.mrr(retrieved, relevant)

        hit_sum += h
        recall_sum += r
        precision_sum += p
        mrr_sum += m

        per_query.append({
            "query": query,
            "hit": int(h),
            "recall": round(r, 3),
            "precision": round(p, 3),
            "mrr": round(m, 3),
        })

    n = len(GOLDEN_DATA) or 1
    return {
        "mode": mode,
        "top_k": top_k,
        "total_queries": len(GOLDEN_DATA),
        "avg_hit_rate": round(hit_sum / n, 3),
        "avg_recall": round(recall_sum / n, 3),
        "avg_precision": round(precision_sum / n, 3),
        "avg_mrr": round(mrr_sum / n, 3),
        "per_query": per_query,
    }
