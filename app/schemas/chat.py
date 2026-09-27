from typing import List

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ChatRequest(BaseModel):
    session_id: str = Field(description="会话ID")
    content: str = Field(description="用户消息")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class RagChatRequest(ChatRequest):
    """RAG 对话请求，在 ChatRequest 基础上追加 RAG 参数"""
    kb_id: List[str] | None = Field(default=None, description="知识库ID列表，为空则全部")


class StopRequest(BaseModel):
    """停止生成请求，只需会话ID（停止不需要消息内容）"""
    session_id: str = Field(description="会话ID")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

