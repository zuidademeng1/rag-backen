"""
上下文压缩组件

在构造 LLM Prompt 前，对长对话历史进行压缩，节省 token。
三种策略：truncate / summarize / hybrid（推荐）
不修改 Memory 中的原始数据，只做读时变换。
"""

from app.components.llm.async_llm import llm_chat
from app.core.get_redis import RedisClient

# Token 估算：中文约 2 字符/token
_CHARS_PER_TOKEN = 2

# 默认阈值：超过此 token 数触发压缩
_DEFAULT_MAX_TOKENS = 4000

# hybrid 模式下保留的最近消息条数
_DEFAULT_KEEP_RECENT = 10

# Redis 键前缀
_REDIS_SUMMARY_PREFIX = "ctx:session:"
_REDIS_SUMMARY_SUFFIX = ":summary"
_REDIS_META_SUFFIX = ":meta"
_REDIS_TTL = 86400  # 24小时

_COMPRESSION_FLAG = "【历史对话摘要】"


def estimate_tokens(messages: list[dict]) -> int:
    """粗略估算消息列表的总 token 数"""
    total = 0
    for msg in messages:
        total += len(msg.get("content", "")) // _CHARS_PER_TOKEN
    return total


def _wrap_summary(summary_text: str) -> dict:
    """将摘要文本包装为 system 消息"""
    return {"role": "system", "content": f"{_COMPRESSION_FLAG}{summary_text}"}


def _is_compression_needed(messages: list[dict], max_tokens: int) -> bool:
    """判断是否需要触发压缩"""
    return estimate_tokens(messages) > max_tokens


#LLM 对话里的消息有几种角色（role）：
# system：系统提示语，设定 AI 的角色、规则、行为等。
# user：用户说的话
# assistant：AI 的回答
#压缩历史时，system 消息要单独挑出来、原样保留在开头，不能被截断掉，否则 AI 就"忘了自己是谁/该遵守什么规则"。
def _truncate(messages: list[dict], keep_recent: int) -> list[dict]:
    """策略：滑动窗口 — 只保留最近 keep_recent 条"""
    system_msgs = [m for m in messages if m.get("role") == "system"]
    history = [m for m in messages if m.get("role") != "system"]
    return system_msgs + history[-keep_recent:]#system 消息原样保留 + 历史只留最近 N 条


async def _summarize(messages: list[dict]) -> str:
    """调用 LLM 生成一段摘要文本"""
    prompt = (
        "请用一段话概括以下对话的核心内容，包括讨论的主题、用户的诉求或偏好、"
        "以及任何已做出的决定或结论。语言简洁，不超过200字。\n\n"
    )
    for m in messages:
        role = "用户" if m["role"] == "user" else "助手"
        prompt += f"{role}：{m['content']}\n"

    resp = await llm_chat(
        [
            {"role": "system", "content": "你是一个专业的对话摘要助手，只输出摘要本身，不要多余的解释。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.strip()


async def _hybrid(messages: list[dict], keep_recent: int) -> list[dict]:
    """策略：早期历史转摘要 + 最近 keep_recent 条原样保留"""
    system_msgs = [m for m in messages if m.get("role") == "system"]
    history = [m for m in messages if m.get("role") != "system"]

    if len(history) <= keep_recent:
        return system_msgs + history

    old = history[:-keep_recent]
    recent = history[-keep_recent:]

    summary_text = await _summarize(old)
    return system_msgs + [_wrap_summary(summary_text)] + recent


async def compress(
    messages: list[dict],
    strategy: str = "hybrid",
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    keep_recent: int = _DEFAULT_KEEP_RECENT,
) -> list[dict]:
    """压缩上下文历史消息

    Args:
        messages: 原始消息列表
        strategy: 压缩策略 truncate | summarize | hybrid
        max_tokens: token 上限，超出才压缩
        keep_recent: 保留的最近消息条数

    Returns:
        压缩后的消息列表，可直接用于 LLM prompt
    """
    if not _is_compression_needed(messages, max_tokens):
        return messages

    if strategy == "truncate":
        return _truncate(messages, keep_recent)
    elif strategy == "summarize":
        return [_wrap_summary(await _summarize(messages))]
    elif strategy == "hybrid":
        return await _hybrid(messages, keep_recent)
    else:
        raise ValueError(f"未知压缩策略: {strategy}")


async def compress_and_save(
    session_id: str,
    messages: list[dict],
    strategy: str = "hybrid",
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    keep_recent: int = _DEFAULT_KEEP_RECENT,
) -> list[dict]:
    """压缩上下文并持久化摘要到 Redis

    返回压缩后的消息列表，同时将摘要存入 Redis，
    下次会话可通过 load_summary() 直接加载。
    """
    result = await compress(messages, strategy, max_tokens, keep_recent)

    # 从结果中提取摘要文本
    summary = None
    #先判断有没有摘要
    has_summary = any(
        m.get("role") == "system" and _COMPRESSION_FLAG in m.get("content", "")
        for m in result
    )
    #有摘要的话，找到摘要并提取
    if has_summary:
        for m in result:
            if m.get("role") == "system" and _COMPRESSION_FLAG in m.get("content", ""):
                summary = m["content"]
                break

    #meta_key 存的是摘要的"元数据"（描述信息），跟摘要正文分开存。
    #所以实际生成两个key：
    #summary_key = "ctx:session:S001:summary"   # 存摘要正文
    #meta_key    = "ctx:session:S001:meta"      # 存元数据
    #summary_key存摘要文本 ，meta_key存压缩参数信息
    if summary:
        summary_key = f"{_REDIS_SUMMARY_PREFIX}{session_id}{_REDIS_SUMMARY_SUFFIX}"
        meta_key = f"{_REDIS_SUMMARY_PREFIX}{session_id}{_REDIS_META_SUFFIX}"
        await RedisClient.set(summary_key, summary, expire=_REDIS_TTL)#给LLM（下次当上下文）
        await RedisClient.set(
            meta_key,
            f'{{"compressed_count":{len(messages)},"keep_recent":{keep_recent}}}',#压缩了多少条，其中保留了多少条
            expire=_REDIS_TTL,
        )
    #"被压缩的对话"本身没有存 Redis——对话原始数据存在 PostgreSQL（ai_session_record 表）。
    # Redis 里存的是压缩后产生的摘要，是个"副产品"，用来下次快速恢复上下文，不用重新读全部历史再压缩一遍。

    return result


async def load_summary(session_id: str) -> str | None:
    """读取该会话上次保存的摘要"""
    key = f"{_REDIS_SUMMARY_PREFIX}{session_id}{_REDIS_SUMMARY_SUFFIX}"
    return await RedisClient.get(key)
