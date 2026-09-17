"""
报告生成流程图编排器

串联多 agent 流水线：
planner → retrieve → writer → polish → revise

整体步骤：
1. 创建报告生成任务，初始化 task_id
2. Planner：使用 LLM 生成报告大纲（流式输出给前端）
3. Retrieve：根据大纲逐章检索知识库素材
4. Writer：按大纲+素材逐章撰写正文（流式输出）
5. Polish：逐章润色（流式输出）
6. Revise：全篇修订审核，输出修改意见和终稿
7. 保存最终结果到 Redis，更新任务状态
"""

from typing import AsyncGenerator

from app.agent.report.base_report_agent import BaseReportAgent
from app.agent.report.planner import ReportPlannerAgent
from app.agent.report.writer import ReportWriterAgent


class ReportGraph(BaseReportAgent):
    """报告流程图编排器"""

    agent_name = "report_graph"

    STEP_PLANNER = "planner"
    STEP_RETRIEVE = "retrieve"
    STEP_WRITER = "writer"
    STEP_POLISH = "polish"
    STEP_REVISE = "revise"

    def __init__(self):
        super().__init__()
        # TODO: 初始化子 agent
        self.planner = ReportPlannerAgent()
        # self.retriever = ReportRetrieverAgent()
        self.writer = ReportWriterAgent()
        # self.polisher = ReportPolishAgent()
        # self.revise = ReportReviseAgent()

    async def run_agent(self, **kwargs) -> AsyncGenerator[str, None]:
        """编排完整的报告生成流程"""
        # ==== 1. 获取参数 ====
        query = kwargs.get("query", "")
        task_id = kwargs.get("task_id")

        self.set_task_id(task_id)
        await self.update_task_status(self.TASK_STATUS_RUNNING)

        # ---- Step 1: 生成大纲 ----
        await self.push_step_progress("正在生成报告大纲...")
        chapters = []  # 保存完整大纲
        async for chunk in self.planner.run_agent(query=query, task_id=task_id):
            yield  chunk  # 流式输出
            chapters.append(chunk)
        chapters = "".join(chapters)

        # ---- Step 2: 逐章检索素材 ----
        await self.push_step_progress("正在检索素材...")
        # 根据大纲检索片段
        materials = {}  # 占位

        # ---- Step 3: 逐章撰写 ----
        await self.push_step_progress("正在撰写报告正文...")
        reports = []  # 保存完整大纲
        async for chunk in self.writer.run_agent(query=query, task_id=task_id):
            yield  chunk  # 流式输出
            reports.append(chunk)
        reports = "".join(reports)

        # ---- Step 4: 逐章润色 ----
        # await self.push_step_progress("正在润色报告...")
        # TODO: await self.polisher.run_agent(full_text=full_text, task_id=task_id)
        # TODO: 接收润色后的逐章内容
        # TODO: yield 每个 chunk 给前端
        polished_text = ""  # 占位

        # ---- Step 5: 全篇修订 ----
        # await self.push_step_progress("正在审核修订...")
        # TODO: await self.revise.run_agent(full_text=polished_text, task_id=task_id)
        # TODO: 接收修订意见 + 最终文本
        # TODO: yield 最终结果
        # final_text = ""  # 占位

        # ---- 6. 保存最终结果 ----
        # await self.save_task_data("final", {
        #     "query": query,
        #     "outline": outline,
        #     "content": final_text,
        # })
        # await self.update_task_status(self.TASK_STATUS_FINISHED)
        # yield final_text
