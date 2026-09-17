import logging
import time
from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.config import settings

logger = logging.getLogger("sqlalchemy.engine")


def build_async_database_url() -> str:
    if settings.db_type == 'postgresql':
        return (
            f'postgresql+asyncpg://{settings.db_username}:{quote_plus(settings.db_password)}@'
            f'{settings.db_host}:{settings.db_port}/{settings.db_database}'
        )
    return (
        f'mysql+asyncmy://{settings.db_username}:{quote_plus(settings.db_password)}@'
        f'{settings.db_host}:{settings.db_port}/{settings.db_database}'
    )


ASYNC_DATABASE_URL = build_async_database_url()


class Base(AsyncAttrs, DeclarativeBase):
    pass


async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    max_overflow=settings.db_max_overflow,
    pool_size=settings.db_pool_size,
    pool_recycle=settings.db_pool_recycle,
    pool_timeout=settings.db_pool_timeout,
)

#1. @event.listens_for(...) 是什么：SQLAlchemy 的事件系统，让你能"监听"数据库引擎的特定事件，事件发生时自动调用你的函数。
#2. 事件参数：async_engine.sync_engine 是监听的引擎对象，"before_cursor_execute" 是监听的事件名称。
#2. 事件参数：conn — 数据库连接对象，cursor — 数据库游标对象，statement — SQL 语句对象，parameters — SQL 语句参数，context — 执行上下文对象，executemany — 是否执行批量插入。
# SQL 执行前：记录开始时间
@event.listens_for(async_engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn._query_start_time = time.time()

# SQL 执行后：计算耗时，慢的话告警
@event.listens_for(async_engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn._query_start_time
    if total > settings.db_slow_query:
        logger.warning("SLOW SQL (%.3fs): %s", total, statement)


AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=async_engine,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取数据库会话，统一管理事务生命周期"""
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
