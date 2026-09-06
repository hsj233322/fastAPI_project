# core/tool_context.py
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis


@dataclass
class ToolContext:
    """
    工具执行上下文，集中注入所有依赖，工具函数按需取用。

    这样可以统一工具函数签名为 (ctx: ToolContext, **params)，
    新增工具无需修改 Agent 循环的调用代码。
    """
    redis: Redis
    user_id: int
    db: AsyncSession | None = None  # 按需提供，不是所有工具都需要数据库
