from typing import Any

from redis.asyncio import ConnectionPool, Redis

from app.config.config import settings

"""
redis连接客户端
"""


class RedisClient:
    _pool: ConnectionPool | None = None

    """
    创建连接池
    """

    @classmethod
    async def _get_pool(cls) -> ConnectionPool:
        if cls._pool is None:
            cls._pool = ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
                db=settings.redis_database,
                decode_responses=True,
            )
        return cls._pool

    """获取连接"""

    @classmethod
    async def get_client(cls) -> Redis:
        pool = await cls._get_pool()
        return Redis.from_pool(pool)

    """关闭连接"""

    @classmethod
    async def close(cls) -> None:
        if cls._pool:
            await cls._pool.disconnect()
            cls._pool = None

    # ==================== 封装redis相关操作  ====================

    """
    获取指定键的值
    key: 键名
    Returns: 键对应的值，不存在时返回None
    """

    @classmethod
    async def get(cls, key: str) -> str | None:
        conn = await cls.get_client()
        return await conn.get(key)

    """
    设置键值对
    Args:
        key: 键名
        value: 值
        expire: 过期时间（秒），不传则永不过期
    Returns: 设置成功返回True
    """

    @classmethod
    async def set(cls, key: str, value: Any, expire: int | None = None) -> bool:
        conn = await cls.get_client()
        return await conn.set(key, value, ex=expire)

    """
    删除指定键
    Args: key: 键名
    Returns: 删除成功返回True，键不存在返回False
    """

    @classmethod
    async def delete(cls, key: str) -> bool:
        conn = await cls.get_client()
        return await conn.delete(key) > 0

    """
    判断键是否存在
    Args:key: 键名
    Returns: 存在返回True，否则返回False
    """

    @classmethod
    async def exists(cls, key: str) -> bool:
        conn = await cls.get_client()
        return await conn.exists(key) > 0

    """
    设置键的过期时间
    Args:
        key: 键名
        seconds: 过期时间（秒）
    Returns:设置成功返回True
    """

    @classmethod
    async def expire(cls, key: str, seconds: int) -> bool:
        conn = await cls.get_client()
        return await conn.expire(key, seconds)

    """
    将键的值自增1（原子操作）
    Args:key: 键名
    Returns:自增后的值
    """

    @classmethod
    async def incr(cls, key: str) -> int:
        conn = await cls.get_client()
        return await conn.incr(key)

    """
    将键的值自减1（原子操作）
    Args:key: 键名
    Returns:自减后的值
    """
    @classmethod
    async def decr(cls, key: str) -> int:
        conn = await cls.get_client()
        return await conn.decr(key)

    # ==================== Hash 类型 ====================

    """
    获取哈希表中指定字段的值
    Args:
        key: 哈希表键名
        field: 字段名
    Returns: 字段值，不存在时返回None
    """
    @classmethod
    async def hget(cls, key: str, field: str) -> str | None:
        conn = await cls.get_client()
        return await conn.hget(key, field)

    @classmethod
    async def hset(cls, key: str, field: str, value: Any) -> int:
        """设置哈希表中指定字段的值

        Args:
            key: 哈希表键名
            field: 字段名
            value: 字段值

        Returns:
            新增字段返回1，覆盖旧字段返回0
        """
        conn = await cls.get_client()
        return await conn.hset(key, field, value)

    @classmethod
    async def hgetall(cls, key: str) -> dict:
        """获取哈希表中所有字段和值

        Args:
            key: 哈希表键名

        Returns:
            包含所有字段和值的字典
        """
        conn = await cls.get_client()
        return await conn.hgetall(key)

    @classmethod
    async def hdel(cls, key: str, field: str) -> bool:
        """删除哈希表中指定字段

        Args:
            key: 哈希表键名
            field: 字段名

        Returns:
            删除成功返回True，字段不存在返回False
        """
        conn = await cls.get_client()
        return await conn.hdel(key, field) > 0

    @classmethod
    async def hexists(cls, key: str, field: str) -> bool:
        """判断哈希表中指定字段是否存在

        Args:
            key: 哈希表键名
            field: 字段名

        Returns:
            存在返回True，否则返回False
        """
        conn = await cls.get_client()
        return await conn.hexists(key, field)

    @classmethod
    async def hkeys(cls, key: str) -> list:
        """获取哈希表中所有字段名

        Args:
            key: 哈希表键名

        Returns:
            包含所有字段名的列表
        """
        conn = await cls.get_client()
        return await conn.hkeys(key)

    @classmethod
    async def hvals(cls, key: str) -> list:
        """获取哈希表中所有字段值

        Args:
            key: 哈希表键名

        Returns:
            包含所有字段值的列表
        """
        conn = await cls.get_client()
        return await conn.hvals(key)

    @classmethod
    async def hlen(cls, key: str) -> int:
        """
        获取哈希表中字段的数量
        Args:
            key: 哈希表键名
        Returns:
            字段数量
        """
        conn = await cls.get_client()
        return await conn.hlen(key)

    # ==================== List 类型 ====================

    @classmethod
    async def lpush(cls, key: str, *values: Any) -> int:
        conn = await cls.get_client()
        return await conn.lpush(key, *values)

    @classmethod
    async def rpush(cls, key: str, *values: Any) -> int:
        conn = await cls.get_client()
        return await conn.rpush(key, *values)

    @classmethod
    async def lpop(cls, key: str) -> str | None:
        conn = await cls.get_client()
        return await conn.lpop(key)

    @classmethod
    async def rpop(cls, key: str) -> str | None:
        conn = await cls.get_client()
        return await conn.rpop(key)

    @classmethod
    async def lrange(cls, key: str, start: int = 0, end: int = -1) -> list:
        conn = await cls.get_client()
        return await conn.lrange(key, start, end)

    @classmethod
    async def llen(cls, key: str) -> int:
        conn = await cls.get_client()
        return await conn.llen(key)

    @classmethod
    async def lrem(cls, key: str, count: int, value: Any) -> int:
        conn = await cls.get_client()
        return await conn.lrem(key, count, value)

    @classmethod
    async def ltrim(cls, key: str, start: int, stop: int) -> None:
        """
        修剪列表，只保留指定范围内的元素
        Args:
            key: 列表键名
            start: 起始索引
            stop: 结束索引
        """
        conn = await cls.get_client()
        await conn.ltrim(key, start, stop)

    @classmethod
    async def hmset(cls, key: str, mapping: dict) -> None:
        """
        批量设置哈希表字段（hset 已取代 hmset，此方法保持语义兼容）
        Args:
            key: 哈希表键名
            mapping: 字段-值映射字典
        """
        conn = await cls.get_client()
        await conn.hset(key, mapping=mapping)

    # ==================== Set 类型 ====================

    @classmethod
    async def sadd(cls, key: str, *members: Any) -> int:
        conn = await cls.get_client()
        return await conn.sadd(key, *members)

    """
    从集合中移除一个或多个成员
    Args:
    key: 集合键名
    *members: 要移除的成员
    Returns:实际移除的成员数量
    """

    @classmethod
    async def srem(cls, key: str, *members: Any) -> int:
        conn = await cls.get_client()
        return await conn.srem(key, *members)

    """
    获取集合中的所有成员
    Args:key: 集合键名
    Returns:包含所有成员的集合
    """

    @classmethod
    async def smembers(cls, key: str) -> set:
        conn = await cls.get_client()
        return await conn.smembers(key)

    """
    判断成员是否在集合中
    Args:
        key: 集合键名
        member: 要判断的成员
    Returns:存在返回True，否则返回False
    """

    @classmethod
    async def sismember(cls, key: str, member: Any) -> bool:
        conn = await cls.get_client()
        return await conn.sismember(key, member)

    """
    获取集合的成员数量
    Args:key: 集合键名
    Returns:成员数量
    """

    @classmethod
    async def scard(cls, key: str) -> int:
        conn = await cls.get_client()
        return await conn.scard(key)

    """
    获取多个集合的交集
    Args:*keys: 集合键名列表
    Returns:交集结果集合
    """

    @classmethod
    async def sinter(cls, *keys: str) -> set:
        conn = await cls.get_client()
        return await conn.sinter(*keys)

    """
    获取多个集合的并集
    Args:*keys: 集合键名列表
    Returns:并集结果集合
    """

    @classmethod
    async def sunion(cls, *keys: str) -> set:
        conn = await cls.get_client()
        return await conn.sunion(*keys)

    # ==================== ZSet 类型 ====================

    @classmethod
    async def zadd(cls, key: str, mapping: dict, nx: bool = False) -> int:
        conn = await cls.get_client()
        return await conn.zadd(key, mapping, nx=nx)

    @classmethod
    async def zrem(cls, key: str, *members: Any) -> int:
        conn = await cls.get_client()
        return await conn.zrem(key, *members)

    @classmethod
    async def zrange(cls, key: str, start: int = 0, end: int = -1, desc: bool = False,
                     withscores: bool = False) -> list:
        conn = await cls.get_client()
        return await conn.zrange(key, start, end, desc=desc, withscores=withscores)

    @classmethod
    async def zscore(cls, key: str, member: Any) -> float | None:
        conn = await cls.get_client()
        return await conn.zscore(key, member)

    @classmethod
    async def zcard(cls, key: str) -> int:
        conn = await cls.get_client()
        return await conn.zcard(key)

    @classmethod
    async def zrank(cls, key: str, member: Any) -> int | None:
        conn = await cls.get_client()
        return await conn.zrank(key, member)

    @classmethod
    async def zrevrank(cls, key: str, member: Any) -> int | None:
        conn = await cls.get_client()
        return await conn.zrevrank(key, member)

    @classmethod
    async def zcount(cls, key: str, min_score: float, max_score: float) -> int:
        conn = await cls.get_client()
        return await conn.zcount(key, min_score, max_score)

    """
    测试Redis连接是否正常
    Returns:连接成功返回True，失败返回False
    """

    @classmethod
    async def test_connection(cls) -> bool:
        try:
            conn = await cls.get_client()
            await conn.ping()
            return True
        except Exception:
            return False


if __name__ == "__main__":
    import asyncio


    async def main():
        print("Redis 连接成功" if await RedisClient.test_connection() else "Redis 连接失败")
        await RedisClient.close()


    asyncio.run(main())
