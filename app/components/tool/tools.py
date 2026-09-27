from app.components.rag.rag_retrieval import rag_research
from app.components.tool.types import ToolDef, ToolResult

# -------- 动态工具注册 --------

_tools: list[ToolDef] = []

"""工具注册函数"""
def register_tool(name: str, description: str, fn: callable, parameters: dict | None = None):
    _tools.append(ToolDef(name=name, description=description, fn=fn, parameters=parameters))



def get_tool(name: str) -> ToolDef | None:
    for t in _tools:
        if t.name == name:
            return t
    return None


def list_tools() -> list[ToolDef]:
    return _tools


async def call_tool(name: str, **kwargs) -> ToolResult:
    tool = get_tool(name)
    if not tool:
        return ToolResult(success=False, error=f"工具不存在: {name}")
    try:
        data = await tool.fn(**kwargs)
        return ToolResult(success=True, data=data)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# -------- 注册工具 --------

register_tool(
    name="knowledge_retrieval",
    description="从知识库中检索与问题相关的内容片段",
    fn=rag_research,
    parameters={
        "query": {"type": "string", "description": "检索问题"},
        "kb_ids": {"type": "array", "description": "知识库ID列表，为空查全部公共库"},
        "top_k": {"type": "int", "description": "返回结果数量"},
    },
)
