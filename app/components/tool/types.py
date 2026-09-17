from dataclasses import dataclass, field
from typing import Any

"""
Agent 运行时的上下文信息
"""
@dataclass
class AgentContext:
    user_id: int
    dept_id: int | None = None
    session_id: str = "default"

"""
工具调用后的统一返回值
"""
@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None

"""
工具的元信息定义
"""
@dataclass
class ToolDef:
    name: str
    description: str
    fn: callable
    parameters: dict | None = None
