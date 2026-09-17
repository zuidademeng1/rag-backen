from openai import AsyncOpenAI, APITimeoutError, APIConnectionError, APIStatusError  # 导入 异步版本 的 OpenAI 客户端

from app.config.config import settings

_client: AsyncOpenAI | None = None

"""
得到异步的llm客户端
"""
def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    return _client


"""
非流式输出
"""
async def llm_chat(messages: list[dict], temperature: float = 0.7) -> str:
    client = _get_client()
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
        stream=False,
    )
    return resp.choices[0].message.content or ""

"""
流式输出，每次 yield 一个文本块
"""
async def llm_chat_stream(messages: list[dict], temperature: float = 0.7):

    client = _get_client()
    stream = None
    try:
        stream = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
    except (APITimeoutError, APIConnectionError) as e:
        yield _error_event("llm_unavailable", f"LLM 服务不可用：{str(e)}")
        return
    except APIStatusError as e:
        yield _error_event("llm_status_error", f"LLM 状态异常：{e.status_code}")
        return
    # 抛出未知异常
    except Exception:
        yield _error_event("internal_error", "服务内部错误")
        raise  # 未知异常还是要抛，让全局异常处理器兜底

    try:
        async for chunk in stream:## 异步遍历流，每迭代一次拿到一块文本块
            #大模型流式返回时，不是一次性给完整回答，而是一块一块（chunk）吐出来的。
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta#取第一个choice（候选）的delta（增量内容）
            if delta.content:
                yield delta.content## 把这段文字 yield 出去给前端
            # 判断生成终止条件
            # stop=正常回答完毕  length=触发上下文长度截断
            if chunk.choices[0].finish_reason in ("stop", "length"):#finish_reason 是生成结束的原因，两种情况：stop正常回答完毕，length触发上下文长度截断。
                break
    finally:
        # 主动关闭流
        await stream.close()
    # try:
    #     stream = await client.chat.completions.create(
    #         model=settings.llm_model,
    #         messages=messages,
    #         temperature=temperature,
    #         stream=True,
    #     )
    #     async for chunk in stream:
    #         # 过滤空白
    #         delta = chunk.choices[0].delta if chunk.choices else None
    #         if delta and delta.content:
    #             yield delta.content
    # finally:
    #     if stream is not None:
    #         await stream.close()

"""
定义错误事件
"""
def _error_event(code: str, message: str) -> dict:
    return {"_type": "error", "code": code, "message": message}


if __name__ == '__main__':
    import asyncio

    messages = [
        {"role": "system", "content": "你是一个AI助手"},
        {"role": "user", "content": "用一句话介绍什么是RAG"},
    ]

    async def main():
        # print("=" * 40)
        # print("非流式输出:")
        # print("-" * 40)
        # result = await llm_chat(messages)
        # print(result)

        print()
        print("=" * 40)
        print("流式输出:")
        print("-" * 40)
        async for chunk in llm_chat_stream(messages):
            print(chunk, end="", flush=True)
        print()
        print("=" * 40)

    asyncio.run(main())
