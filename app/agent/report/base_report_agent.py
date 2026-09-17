from abc import ABC
from typing import Optional, Dict, Any

from app.agent.base_agent import BaseAgent
from app.core.get_redis import RedisClient


"""
报告,文档撰写多智能体 专属基类
所有报告相关Agent都继承此类：
planner / retrieve / writer / polish / revise
规划 - 检索 - 写作 - 润色 - 修正
"""
class BaseReportAgent(BaseAgent, ABC):


    # 任务状态常量 统一规范
    TASK_STATUS_PENDING = "pending"
    TASK_STATUS_RUNNING = "running"
    TASK_STATUS_FINISHED = "finished"
    TASK_STATUS_FAILED = "failed"

    def __init__(self):
        # 每个子实例可持有 task_id
        self.task_id: Optional[str] = None

    """设置当前任务ID"""
    def set_task_id(self, task_id: str) -> None:
        self.task_id = task_id

    async def update_task_status(self, status: str) -> None:
        """更新任务状态到Redis"""
        if not self.task_id:
            return
        key = f"report:task:{self.task_id}:status"
        await RedisClient.set(key, status)

    """
    推送当前步骤进度信息
    可对接 WebSocket / Redis PubSub 给前端实时展示
    :param step_msg: 步骤文案 例如：正在生成报告大纲、正在撰写第一章
    """
    async def push_step_progress(self, step_msg: str) -> None:
        if not self.task_id:
            return
        # 1. 把进度存入Redis 留作前端轮询兜底
        progress_key = f"report:task:{self.task_id}:progr ess"
        await RedisClient.lpush(progress_key, step_msg)
        # 限制只保留最近20条
        await RedisClient.ltrim(progress_key, 0, 19)

        # 2. 后续可扩展：在这里统一发 WebSocket / Redis发布订阅
        # await websocket_broadcast(self.task_id, step_msg)

    async def save_task_data(self, data_key: str, data: Dict[str, Any]) -> None:
        """
        保存任务中间数据（大纲、章节、资料等）
        :param data_key: 自定义key outline / chapters / materials
        :param data: 字典结构化数据
        """
        if not self.task_id:
            return
        key = f"report:task:{self.task_id}:{data_key}"
        await RedisClient.hmset(key, data)