"""端到端 RAG 评估：检索 + LLM 生成，再用 LLM Judge 打分。

对每条黄金数据：检索 top_k 分块 → 拼 prompt 生成答案 → 用 LLM Judge
评估 faithfulness（忠实度/有无幻觉）和 relevance（相关性/是否切题）。
"""

import json

from app.components.llm.async_llm import llm_chat
from app.components.rag.rag_retrieval import rag_research
from app.eval.golden_data import GOLDEN_DATA

_JUDGE_SYSTEM = (
    "你是一个 RAG 系统评估专家。请根据给定的【资料】、【用户问题】、"
    "【标准答案】和【AI 生成的答案】，评估 AI 答案的质量。"
    "只输出一个 JSON 对象，不要输出任何其他文字，格式如下：\n"
    '{"faithfulness": 1-5, "relevance": 1-5}\n'
    "faithfulness（忠实度）：答案是否完全基于资料、有无编造或幻觉（5=完全基于资料，1=大量幻觉）。\n"
    "relevance（相关性）：答案是否准确回答了问题、与标准答案是否一致（5=完全正确，1=完全错误）。"
)


def _build_judge_messages(context: str, query: str, ground_truth: str, answer: str) -> list[dict]:
    prompt = (
        f"资料：\n{context}\n\n"
        f"用户问题：{query}\n\n"
        f"标准答案：{ground_truth}\n\n"
        f"AI 生成的答案：{answer}"
    )
    return [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {"role": "user", "content": prompt},
    ]


def _parse_judge_result(text: str) -> tuple[float, float] | None:
    """解析 LLM Judge 返回的 JSON，失败返回 None。"""
    try:
        data = json.loads(text.strip())
        return float(data["faithfulness"]), float(data["relevance"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # 尝试从文本中提取 JSON 片段
        import re
        m = re.search(r'\{[^{}]*"faithfulness"[^{}]*\}', text)
        if m:
            try:
                data = json.loads(m.group())
                return float(data["faithfulness"]), float(data["relevance"])
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                return None
        return None


async def evaluate_rag(top_k: int = 5) -> dict:
    """端到端 RAG 评估。

    Returns:
        汇总报告 dict，含每个 query 的生成答案、Judge 打分和整体平均分
    """
    per_query = []
    faith_sum = 0.0
    rel_sum = 0.0
    valid_count = 0

    for item in GOLDEN_DATA:
        query = item["query"]
        ground_truth = item["ground_truth"]

        # 1. 检索
        results = await rag_research(query=query, top_k=top_k, mode="hybrid")
        context = "\n\n".join(r.get("content", "") for r in results)

        # 2. 生成（复用 chat_service 的拼 prompt 逻辑）
        user_augmented = f"请基于以下资料回答问题。\n\n资料：\n{context}\n\n用户问题：{query}"
        answer = await llm_chat(
            [
                {"role": "system", "content": "你是一个AI助手"},
                {"role": "user", "content": user_augmented},
            ],
            temperature=0.1,
        )

        # 3. LLM Judge 打分
        judge_messages = _build_judge_messages(context, query, ground_truth, answer)
        judge_text = await llm_chat(judge_messages, temperature=0.1)
        parsed = _parse_judge_result(judge_text)

        faith = parsed[0] if parsed else None
        rel = parsed[1] if parsed else None
        if faith is not None:
            faith_sum += faith
            rel_sum += rel
            valid_count += 1

        per_query.append({
            "query": query,
            "ground_truth": ground_truth,
            "answer": answer,
            "faithfulness": faith,
            "relevance": rel,
        })

    n = valid_count or 1
    return {
        "top_k": top_k,
        "total_queries": len(GOLDEN_DATA),
        "valid_judged": valid_count,
        "avg_faithfulness": round(faith_sum / n, 2),
        "avg_relevance": round(rel_sum / n, 2),
        "per_query": per_query,
    }
