from abc import ABC, abstractmethod
from typing import Dict, Any

"""
agent的基类
"""
class BaseAgent(ABC):
    agent_name: str = ""

    """
    agent run 函数
    """
    @abstractmethod
    async def run_agent(self, **kwargs) -> Dict[str, Any]:
        pass