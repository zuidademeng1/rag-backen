import json
from typing import List, Dict, Any

from app.core.get_redis import RedisClient

"""
记忆组件
短时记忆存放redis缓存--短期记忆就是会话记忆
长期记忆指的是用户画像，用户喜好等
"""


class Memory:
    __MESSAGE_LIMIT = 50  # 最大保留消息条数

    """
    保存一条对话到短时记忆
    """

    @classmethod
    async def save_message(cls, session_id: str, role: str, content: str):
        key = f"chat:msg:{session_id}"
        message = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        # 加入列表-列表就是消息队列
        await RedisClient.rpush(key, message)
        # 限制最多保存 N 条  开始索引，结束索引
        await RedisClient.ltrim(key, -cls.__MESSAGE_LIMIT, -1)

    """
    获取对话历史
    """

    @classmethod
    async def get_messages(cls, session_id: str) -> List[Dict[str, str]]:
        key = f"chat:msg:{session_id}"
        messages = await RedisClient.lrange(key, 0, -1)
        # 把 JSON 字符串转回字典
        return [json.loads(msg) for msg in messages]

    """
    清空当前会话记忆
    """

    @classmethod
    async def clear_history(cls, session_id: str):
        key = f"chat:msg:{session_id}"
        await RedisClient.delete(key)

    """
    保存会话状态（当前意图、步骤、槽位信息）
    """

    @classmethod
    async def set_state(cls, session_id: str, state: Dict[str, Any]):
        key = f"chat:msg:{session_id}"
        if state:
            await RedisClient.hmset(key, state)

    """
    获取会话状态
    """

    @classmethod
    async def get_state(cls, session_id: str) -> Dict[str, str]:
        key = f"chat:msg:{session_id}"
        return await RedisClient.hgetall(key)
        #hgetall(key) 是 Redis 的 Hash（哈希）类型 命令，作用是一次性取出某个 key 下所有的 field-value 键值对，返回一个字典。