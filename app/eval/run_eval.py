"""RAG 评估入口：跑检索层 + 端到端两层评估并打印报告。

运行方式（项目根目录、venv 激活状态）：
    python -m app.eval.run_eval
"""

import asyncio
import json

from app.core.get_milvus import MilvusClient
from app.eval.rag_eval import evaluate_rag
from app.eval.retrieval_eval import evaluate_retrieval


async def main():
    # 评估脚本是独立进程，不会走主后端的 lifespan，需手动连接 Milvus
    await MilvusClient.connect()
    try:
        await _run()
    finally:
        await MilvusClient.close()


async def _run():
    print("=" * 60)
    print("检索层评估（纯检索，不经过 LLM）")
    print("=" * 60)
    ret = await evaluate_retrieval(top_k=5, mode="hybrid")
    print(f"模式: {ret['mode']}  top_k: {ret['top_k']}")
    print(f"平均命中率(Hit@5): {ret['avg_hit_rate']}")
    print(f"平均召回率(Recall): {ret['avg_recall']}")
    print(f"平均精确率(Precision): {ret['avg_precision']}")
    print(f"平均MRR: {ret['avg_mrr']}")
    print("\n明细：")
    for q in ret["per_query"]:
        print(f"  [{q['hit']}] {q['query']}  recall={q['recall']} precision={q['precision']} mrr={q['mrr']}")

    print()
    print("=" * 60)
    print("端到端评估（检索 + LLM 生成 + LLM Judge）")
    print("=" * 60)
    rag = await evaluate_rag(top_k=5)
    print(f"有效评测条数: {rag['valid_judged']}/{rag['total_queries']}")
    print(f"平均忠实度(Faithfulness): {rag['avg_faithfulness']}")
    print(f"平均相关性(Relevance): {rag['avg_relevance']}")
    print("\n明细：")
    for q in rag["per_query"]:
        print(f"  Q: {q['query']}")
        print(f"  标准答案: {q['ground_truth']}")
        print(f"  生成答案: {q['answer'][:80]}{'...' if len(q['answer']) > 80 else ''}")
        print(f"  Judge: faithfulness={q['faithfulness']}, relevance={q['relevance']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
