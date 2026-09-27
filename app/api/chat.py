import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.permission import RequirePermission
from app.dao.session_dao import SessionDao
from app.schemas.chat import ChatRequest, RagChatRequest, StopRequest
from app.services.chat_service import ChatWithLLMService
from app.utils.auth_util import AuthUtil, CurrentUser
from app.utils.response_util import ResponseUtil

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:talk")),
):
    session = await SessionDao.get_by_id(db, body.session_id)
    if not session:  
        raise HTTPException(status_code=404, detail="会话不存在")

    async def event_stream():
        async for event in ChatWithLLMService.chat_stream(db, body.session_id, body.content, user):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/rag-stream")
async def chat_rag_stream(
    body: RagChatRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:chat:talk")),
):
    session = await SessionDao.get_by_id(db, body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    async def event_stream():
        async for event in ChatWithLLMService.chat_rag_stream(
            db, body.session_id, body.content, user,
            kb_id=body.kb_id,
        ):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stop")
async def chat_stop(
    body: StopRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(AuthUtil.get_current_user),
):
    """停止当前会话正在生成的回复（在 Redis 设置停止标志，由流式循环检查）"""
    from app.core.get_redis import RedisClient

    await RedisClient.set(f"chat:stop:{body.session_id}", "1", expire=300)
    return ResponseUtil.success(msg="已发送停止信号")



#http协议--懒惰的服务员
#http协议，是无状态的单次请求，只能客户端向服务器端单次发送请求
#只能是一问一答的方式，服务器无法向客户端主动推送消息，只能等待客户端来询问，才能回答
#如果是比较耗时的后端操作，客户端只能不断地轮询服务器查看服务进度的状态
#典型场景：普通接口查询，网页加载，提交表单等

#SSE协议--勤快的服务员
#SSE全程server-sent-events，是http协议的一种变体，客户端发送一次http请求后，服务器端会一直主动推送消息直到结束
#典型场景：大语言模型的流式输出，外卖进度等
#SSE只能推送文本数据，实现难度中等

#典型SSE协议交互过程：
#1.客户端通过普通HTTP请求连接服务器
#2.服务器返回一个特殊的相应类型，也就是事件流：Content-Type: text/event-stream，标志是流式输出
#3.这个HTTP连接不会马上结束
#4.服务器可以在这个连接里不断写入事件数据
#5.浏览器通过EventSource对象监听这个连接，当服务器写入事件数据时，会自动解析并渲染到页面上

#客户端发送HTTP请求之后，服务器的响应头如下：
#Content-Type: text/event-stream
#Cache-Control: no-cache
#Connection: keep-alive#长连接

#SSE消息包含如下4个字段，每条消息用一个空行结束
#1.data 消息内容 
#2.event 事件类型，例如消息就是message
#3.id 事件ID，用于断线重连后续传
#4.retry 重试时间间隔，单位毫秒


#WebSocket协议--随身携带对讲的服务员
#websocket协议，允许客户端和服务器双向通信，都可以主动发起推送。因此在websocket协议下，一定程度上模糊了客户端和服务器的角色
#典型场景：实时聊天，实施互动游戏，股票交易等