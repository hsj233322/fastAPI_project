# core/tool.py
from collections.abc import Awaitable, Callable
from typing import Any

# 工具类 描述一个工具的名称、描述、参数 schema 和执行函数。
class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable[..., Awaitable[Any]],
    ):
        self.name: str = name
        self.description: str = description
        self.parameters: dict[str, Any] = parameters
        self.func: Callable[..., Awaitable[Any]] = func

    # 给 OpenAI 模型的 Function Calling 配置使用
    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }