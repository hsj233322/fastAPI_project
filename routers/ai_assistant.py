# AI助手路由，处理AI相关请求
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from redis.asyncio import Redis

from config.db_config import get_db
from config.redis_config import get_redis
from schemas import ApiResponse
from schemas.ai_assistant import ChatRequest, ChatResponse
from services.deepseek_service import DeepSeekService
from utils.auth import get_current_user
from models.users import User

router = APIRouter(prefix="/api/ai", tags=["AI助手"])

deepseek_service = DeepSeekService()


async def rate_limit(
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    """使用Redis实现频率限制：每分钟最多10次请求"""
    rate_key = f"ai:rate:{user.id}"
    count = await redis.incr(rate_key)

    if count == 1:
        await redis.expire(rate_key, 60)

    if count > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )


@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat_with_ai(
    chat_request: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(rate_limit)],
):
    if not deepseek_service.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务暂未配置，请联系管理员",
        )

    reply, related_jobs = await deepseek_service.chat(
        db=db,
        message=chat_request.message,
        conversation_history=chat_request.conversation_history,
    )

    response = ChatResponse(reply=reply, related_jobs=related_jobs)
    return ApiResponse(data=response)