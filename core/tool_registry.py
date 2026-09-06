# core/tool_registry.py
import logging
from typing import Any

from pydantic import BaseModel

from core.tool import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表：集中管理所有工具，支持按名称查找、获取 OpenAI schema 列表。

    Agent 循环不再硬编码工具列表，而是从注册表获取，便于：
    - 模块化注册（各模块通过 @tool 装饰器自行注册）
    - 按权限过滤工具
    - 测试时 mock 替换
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具名冲突: {tool.name}")
        self._tools[tool.name] = tool
        logger.debug(f"已注册工具: {tool.name}")

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_all(self) -> list[Tool]:
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI Function Calling schema。"""
        return [t.to_openai_schema() for t in self._tools.values()]


# 全局默认注册表
default_registry = ToolRegistry()


def tool(
    name: str,
    description: str,
    params_model: type[BaseModel] | None = None,
):
    """
    装饰器：把异步函数注册为工具。

    用法：
        @tool(name="search_jobs", description="...", params_model=SearchJobsParams)
        async def search_jobs_func(ctx, query, location=None):
            ...
    """
    def decorator(func):
        t = Tool(
            name=name,
            description=description,
            func=func,
            params_model=params_model,
        )
        default_registry.register(t)
        return func

    return decorator
