# tools.py
from collections.abc import Awaitable, Callable
from typing import Any

# 工具类
class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable[..., Awaitable[Any]],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    # 返回 LLM 需要的格式
    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }