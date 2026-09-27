import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.components.llm.async_llm import llm_chat_stream
from app.components.rag.rag_retrieval import rag_research
from app.core.get_redis import RedisClient
from app.schemas.session import RecordAddRequest
from app.services.session_service import SessionService
from app.utils.auth_util import CurrentUser

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是「校园学生事务助手」，负责回答学生关于学校规章制度、办事流程、奖助学金、选课考试、"
    "宿舍后勤、就业实习、国际交流等事务的问题。\n"
    "\n"
    "请严格遵守以下规则：\n"
    "1. 只依据用户提供的「资料」内容回答，绝不编造资料中不存在的条款、金额、日期或流程。\n"
    "2. 资料中没有相关信息的，明确回答「未在学校公开资料中找到相关内容，建议咨询相关部门」，不要猜测。\n"
    "3. 金额、截止日期、所需材料等关键信息必须与资料原文完全一致。\n"
    "4. 涉及学生个人学籍、成绩、奖惩、隐私等个体信息，一律不回答，引导学生前往教务处或学工处咨询。\n"
    "5. 回答简洁、准确、友好，使用中文。"
)


class ChatWithLLMService:
    """
    流式对话，自动保存对话记录。
    """
    @classmethod
    async def chat_stream(cls, db: AsyncSession, session_id: str, content: str, user: CurrentUser, ):

        # 1. 保存用户消息
        user_req = RecordAddRequest(
            session_id=session_id,
            role="user",
            content=content,
            token_count=_estimate_tokens(content),
        )
        await SessionService.add_record(db, user_req, user)

        # 2. 加载历史记录作为上下文
        records = await SessionService.get_records(db, session_id)

        # 3. 组装 LLM 消息列表：system prompt + 历史对话
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for r in records:
            messages.append({"role": r["role"], "content": r["content"]})

        # 4. 调用 LLM 流式输出
        full_content = ""
        agen = None
        stopped = False
        try:
            agen = llm_chat_stream(messages)
            async for item in agen:
                if isinstance(item, dict) and item.get("_type") == "error":
                    yield f"event: error\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"
                    return

                # 检查停止信号
                if await RedisClient.exists(f"chat:stop:{session_id}"):
                    stopped = True
                    break

                full_content += item
                yield f"data: {json.dumps({'token': item}, ensure_ascii=False)}\n\n"

            # 5. 流完成，保存助手回复
            if full_content:
                assistant_req = RecordAddRequest(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    token_count=_estimate_tokens(full_content),
                )
                await SessionService.add_record(db, assistant_req, user)

            # 6. 流结束标记
            yield f"data: {json.dumps({'done': True, 'stopped': stopped}, ensure_ascii=False)}\n\n"

        except GeneratorExit:
            logger.warning("用户 %s 断连，终止流", user.id)
            raise
        finally:
            if stopped:
                await RedisClient.delete(f"chat:stop:{session_id}")
            if agen is not None:
                await agen.aclose()

    """
    RAG 流式对话（骨架），自动保存对话记录。
    
    """
    @classmethod
    async def chat_rag_stream(
        cls, db: AsyncSession, session_id: str, content: str, user: CurrentUser,
        kb_id: list[str] | None = None, mode: str = "hybrid",
    ):

        # 1. 保存用户消息
        user_req = RecordAddRequest(
            session_id=session_id,
            role="user",
            content=content,
            token_count=_estimate_tokens(content),
        )
        await SessionService.add_record(db, user_req, user)

        # 2. 加载历史记录作为上下文
        records = await SessionService.get_records(db, session_id)

        # 3. RAG 检索知识库
        # TODO: 调用 rag_research 从知识库召回相关文档片段
        context_chunks = await rag_research(
              query=content,
              kb_ids=kb_id,
              top_k=5,
              mode=mode,
          )
        print("---------RAG检索结果------------")
        print(context_chunks)

        # 3.5 透出来源（先于 token 发出，前端渲染「来源」）
        sources = [
            {
                "doc_id": c.get("doc_id"),
                "filename": c.get("filename"),
                "content": c.get("content"),
                "chunk_index": c.get("chunk_index"),
                "score": round(c.get("score") or 0, 4),
            }
            for c in context_chunks
        ]
        yield f"data: {json.dumps({'sources': sources}, ensure_ascii=False)}\n\n"

        # 4. 组装 system prompt + 历史对话，并将检索上下文拼接到用户消息
        rag_context = "\n\n".join(c["content"] for c in context_chunks)
        user_augmented = f"请基于以下资料回答问题。\n\n资料：\n{rag_context}\n\n用户问题：{content}"

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for r in records[:-1]:
            messages.append({"role": r["role"], "content": r["content"]})
        # 最后一条用户消息替换为增强后的消息
        messages.append({"role": "user", "content": user_augmented})
        print("---------message--------------")
        print(messages)

        # 5. 调用 LLM 流式输出
        full_content = ""
        agen = None
        stopped = False
        try:
            agen = llm_chat_stream(messages)
            async for item in agen:
                if isinstance(item, dict) and item.get("_type") == "error":
                    yield f"event: error\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"
                    return

                # 检查停止信号
                if await RedisClient.exists(f"chat:stop:{session_id}"):
                    stopped = True
                    break

                full_content += item
                yield f"data: {json.dumps({'token': item}, ensure_ascii=False)}\n\n"

            # 6. 流完成，保存助手回复
            if full_content:
                assistant_req = RecordAddRequest(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    token_count=_estimate_tokens(full_content),
                )
                await SessionService.add_record(db, assistant_req, user)

            # 7. 流结束标记
            yield f"data: {json.dumps({'done': True, 'stopped': stopped}, ensure_ascii=False)}\n\n"

        except GeneratorExit:
            logger.warning("用户 %s 断连，终止流", user.id)
            raise
        finally:
            if stopped:
                await RedisClient.delete(f"chat:stop:{session_id}")
            if agen is not None:
                await agen.aclose()


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数"""
    if not text:
        return 0
    return max(1, len(text) // 2)
