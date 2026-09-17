from typing import AsyncGenerator

from app.agent.base_agent import BaseAgent

"""
单agent
"""


class SingleAgent(BaseAgent):
    agent_name = "single_agent"

    async def run_agent(self, **kwargs) -> AsyncGenerator[str, None]:
        # TODO实现
        # 1.获取参数
        query = kwargs.get("query")
        intent = kwargs.get("intent")  # 两种 chat或者rag_qa

        # 2.加载历史对话

        # 3.构建prompt{}

        # 根据意图选择工具

        # LLM流式输出
