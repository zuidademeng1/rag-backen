import asyncio
import json
import logging
import traceback

from app.core.database import AsyncSessionLocal
from app.core.get_redis import RedisClient
from app.dao.document_dao import DocumentDao
from app.services.document_chunk_service import DocumentChunkService
from app.utils.auth_util import CurrentUser

logger = logging.getLogger("task_worker")

QUEUE_KEY = "doc:parse:queue"

# 类型注解，表示 _stop_event 变量可以是 asyncio.Event 类型或 None
_stop_event: asyncio.Event | None = None


"""
result = await redis.blpop(QUEUE_KEY, timeout=1)
timeout=0 表示无限阻塞，永不超时。它会一直卡在 blpop 这一行，直到队列里有数据才返回。
timeout 参数的三种情况
timeout 值	    行为
0	            无限阻塞，永远等，直到有数据才返回
>0（如 1）	    最多等 N 秒，超时返回 None
负数（如 -1）	也等于无限阻塞（不同客户端约定不同）

所以 timeout=0 时，result is None 这个分支几乎永远不会触发（因为不会因为超时返回 None），它只会一直等。

blpop 是 Redis List 的阻塞弹出命令：
b = blocking（阻塞）
lpop = 从列表左边弹出一个元素（取出来并删掉)
result = await redis.blpop(QUEUE_KEY, timeout=1)
作用：从 QUEUE_KEY 这个列表的左边取出一个元素。
如果队列里有任务 → 立刻取出并返回
如果队列是空的 → 阻塞等待，最多等 timeout=1 秒
1 秒后还是空 → 返回 None
"""


"""文档解析的任务调度"""
async def start_worker():

    global _stop_event
    _stop_event = asyncio.Event()

    redis = await RedisClient.get_client()
    logger.info("后台文档解析 worker 已启动，等待任务...")

    while not _stop_event.is_set():
        try:
            # 阻塞等待任务，超时 1 秒以便检查停止信号
            result = await redis.blpop(QUEUE_KEY, timeout=1)#阻塞等1秒
            if result is None:
                continue#超时了没任务，回到循环顶部，再继续在列表中等任务

            _, payload = result
            # 处理解析任务
            await _process_task(payload)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("worker 循环异常: %s", e)

"""发送停止信号给 worker"""
async def stop_worker():
    global _stop_event
    if _stop_event is not None:
        _stop_event.set()

"""处理单个解析任务"""
async def _process_task(payload: str):
    task = json.loads(payload)
    doc_id = task["doc_id"]
    user = CurrentUser(
        user_id=task["user_id"],
        user_name=task.get("user_name", ""),
        dept_id=task.get("dept_id"),
    )

    logger.info("开始后台解析文档: doc_id=%s", doc_id)

    async with AsyncSessionLocal() as db:
        try:
            await DocumentChunkService.parse_document(db, doc_id, user)
            await db.commit()
            logger.info("文档解析完成: doc_id=%s", doc_id)
        except Exception as e:
            await db.rollback()
            logger.error("文档解析失败: doc_id=%s, 错误: %s\n%s",
                         doc_id, e, traceback.format_exc())
            # 尝试更新 chunk_status 为 failed
            try:
                doc = await DocumentDao.get_by_id(db, doc_id)
                if doc:
                    doc.chunk_status = "failed"
                    await DocumentDao.update(db, doc)
                    await db.commit()
            except Exception as db_e:
                await db.rollback()
                logger.error("更新文档失败状态异常: %s", db_e)
