from typing import AsyncGenerator

from app.agent.report.base_report_agent import BaseReportAgent
from app.components.llm.async_llm import llm_chat_stream

_SYSTEM_PROMPT = """你是一个专业的报告大纲撰写专家。
根据用户的需求，生成一份结构清晰的报告大纲。
要求：
1. 大纲层级分明，至少包含一级和二级标题
2. 每个章节给出简要说明或撰写要点
3. 格式使用 Markdown 标题符号（# ## ###）
4. 不要输出正文内容，只输出大纲结构"""


class ReportPlannerAgent(BaseReportAgent):
    agent_name = "report_planner"

    async def run_agent(self, **kwargs) -> AsyncGenerator[str, None]:
        query = kwargs.get("query", "")
        task_id = kwargs.get("task_id")

        self.set_task_id(task_id)
        await self.update_task_status(self.TASK_STATUS_RUNNING)
        await self.push_step_progress("正在生成报告大纲...")

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下需求生成报告大纲：\n{query}"},
        ]

        outline_parts: list[str] = []
        async for chunk in llm_chat_stream(messages, temperature=0.5):
            outline_parts.append(chunk)
            yield chunk

        outline = "".join(outline_parts)
        await self.save_task_data("outline", {"outline": outline, "query": query})
        await self.update_task_status(self.TASK_STATUS_FINISHED)


if __name__ == "__main__":
    import asyncio

    async def main():
        agent = ReportPlannerAgent()
        print("=" * 60)
        print("测试 ReportPlannerAgent.run_agent()")
        print("=" * 60)
        result_parts = []
        async for chunk in agent.run_agent(
            query="写一份关于2026年第一季度销售业绩的报告，包含各区域销售数据对比、同比分析、问题总结和改进建议，有些要给出三级标题",
            task_id="test-001",
        ):
            print(chunk, end="", flush=True)
            result_parts.append(chunk)
        print("\n" + "=" * 60)
        print(f"\n生成完成，共 {len(''.join(result_parts))} 字符")

    asyncio.run(main())
