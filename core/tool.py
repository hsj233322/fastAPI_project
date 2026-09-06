# core/tool.py
import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from core.tool_context import ToolContext
from core.tool_errors import (
    ToolError,
    ToolExecutionError,
    ToolParamError,
    ToolTimeoutError,
)

logger = logging.getLogger(__name__)


class Tool:
    """
    工具抽象类：元数据（name/description）+ 参数模型（params_model）+ 执行体（func）。

    - params_model: Pydantic 模型，既用于生成 OpenAI JSON Schema，也用于运行时参数校验。
    - func: 异步执行函数，签名为 (ctx: ToolContext, **params)。
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Awaitable[Any]],
        params_model: type[BaseModel] | None = None,
    ):
        self.name: str = name
        self.description: str = description
        self.func: Callable[..., Awaitable[Any]] = func
        self.params_model = params_model

    def to_openai_schema(self) -> dict[str, Any]:
        """序列化为 OpenAI Function Calling 所需的 JSON 结构。"""
        parameters = (
            self.params_model.model_json_schema() if self.params_model else {}
        )
        # Pydantic 生成的 schema 会带 title 等冗余字段，清理一下让 LLM 更聚焦
        parameters.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }

    async def execute(self, ctx: ToolContext, raw_args: dict[str, Any]) -> Any:
        """
        统一执行入口：参数校验 → 调用函数 → 异常分级。

        返回值为工具执行结果（通常是可序列化的 dict 或 list）。
        """
        try:
            if self.params_model:
                validated = self.params_model.model_validate(raw_args)
                return await self.func(ctx, **validated.model_dump())
            return await self.func(ctx, **raw_args)
        except ValidationError as e:
            raise ToolParamError(f"参数错误: {e.errors()}") from e
        except asyncio.TimeoutError:
            raise ToolTimeoutError()
        except ToolError:
            raise
        except Exception as e:
            logger.exception(f"工具 {self.name} 执行异常")
            raise ToolExecutionError(f"内部错误: {e}", retryable=False) from e
