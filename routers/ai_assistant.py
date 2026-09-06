# routers/ai_assistant.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from redis.asyncio import Redis
from typing import Any

from config.db_config import get_db
from config.redis_config import get_redis
from schemas import ApiResponse
from schemas.ai_assistant import ChatRequest, ChatResponse
from services.deepseek_service import DeepSeekService
from services.session_manager import SessionManager
from utils.auth import get_current_user
from models.users import User
from utils.rate_limit import check_rate_limit
from core.tool_context import ToolContext

router = APIRouter(prefix="/api/ai", tags=["AI助手"])

deepseek_service = DeepSeekService()

async def rate_limit(
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    """AI 对话限流：每分钟最多 10 次请求（基于用户）"""
    key = f"ai:rate:{user.id}"
    allowed = await check_rate_limit(redis, key, max_requests=10, window_seconds=60)
    if not allowed:
        ttl = await redis.ttl(key)
        wait_msg = f"{ttl} 秒后再试" if ttl > 0 else "稍后再试"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求过于频繁，请{wait_msg}",
        )
        
@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat_with_ai(
    chat_request: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    _: Annotated[None, Depends(rate_limit)],
):
    """
    与 AI 助手进行多轮对话。

    接收用户消息和可选会话ID，调用 DeepSeek 大模型生成智能回复，
    并返回关联的职位推荐列表。
    """
    # 1. 会话管理
    session_manager = SessionManager(redis, user.id)
    session_id, history_messages = await session_manager.load_messages(chat_request.session_id) # 加载会话历史消息

    # 2. 构建当前请求消息列表（不含 system prompt）
    current_messages = history_messages + [{"role": "user", "content": chat_request.message}]

    # 3. 构建工具执行上下文并调用 Agent 循环
    ctx = ToolContext(redis=redis, user_id=user.id)
    reply, related_jobs, updated_messages = await deepseek_service.chat(
        ctx=ctx,
        messages=current_messages,
    )

    # 4. 保存更新后的会话
    await session_manager.save_messages(session_id, updated_messages)

    # 5. 构建响应
    response = ChatResponse(
        reply=reply,
        related_jobs=related_jobs,
        session_id=session_id,
    )
    return ApiResponse(data=response)