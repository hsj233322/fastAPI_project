# routers/ai_assistant.py
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Annotated
from redis.asyncio import Redis
from typing import Any

from config.redis_config import get_redis
from schemas.ai_assistant import ChatRequest
from services.deepseek_service import DeepSeekService
from services.session_manager import SessionManager
from utils.auth import get_current_user
from models.users import User
from utils.rate_limit import check_rate_limit
from core.tool_context import ToolContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI助手"])

deepseek_service = DeepSeekService()


def _sse(event: dict[str, Any]) -> str:
    """将事件字典编码为一帧 SSE（data: 单行 JSON + 空行分隔）。"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


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
        
@router.post("/chat/stream")
async def chat_with_ai_stream(
    chat_request: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    _: Annotated[None, Depends(rate_limit)],
):
    """
    与 AI 助手进行多轮对话（SSE 流式输出）。

    事件协议（每帧 `data: {json}\\n\\n`）：
    - {"type": "status", "content": "..."}      工具轮提示
    - {"type": "delta",  "content": "..."}      正文增量
    - {"type": "jobs",   "content": [...]}      相关岗位卡片
    - {"type": "error",  "content": "..."}      出错提示
    - {"type": "done",   "session_id": ...}     结束帧（元数据）

    注意：鉴权 / 限流 / 会话加载均在进入流式响应前完成，
    因此 401 / 429 仍以普通 HTTP 状态码返回；流建立后的异常走 error 事件。
    """
    # 会话管理（进入流之前，异常会以普通 HTTP 错误抛出）
    session_manager = SessionManager(redis, user.id)
    session_id, history_messages = await session_manager.load_messages(chat_request.session_id)

    # 构建当前请求消息列表（不含 system prompt）。
    # service 会原地 append/extend 该列表，流结束后即为完整会话。
    current_messages = history_messages + [{"role": "user", "content": chat_request.message}]

    # 构建工具执行上下文
    ctx = ToolContext(redis=redis, user_id=user.id)

    async def event_generator():
        had_error = False
        try:
            async for event in deepseek_service.chat_stream(
                ctx=ctx, messages=current_messages
            ):
                if event.get("type") == "error":
                    had_error = True
                # jobs 事件本身就是可 JSON 序列化的 dict 列表（工具层返回），直接透传
                yield _sse(event)
        except Exception:
            logger.exception("SSE 流式响应中断")
            had_error = True
            yield _sse({"type": "error", "content": "服务异常，请稍后再试。"})

        # 落库会话：仅在正常结束时保存，避免写入残缺/悬空消息
        if not had_error:
            try:
                await session_manager.save_messages(session_id, current_messages)
            except Exception:
                logger.exception("保存 AI 会话失败，session_id=%s", session_id)
            yield _sse({"type": "done", "session_id": session_id})
        else:
            yield _sse({"type": "done", "session_id": session_id, "error": True})

    return StreamingResponse(
        event_generator(),  # 创建生成器对象
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # 关键：关闭 nginx 缓冲，确保分片即时到达浏览器
            "X-Accel-Buffering": "no",
        },
    )