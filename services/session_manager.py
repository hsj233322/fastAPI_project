# services/session_manager.py

import json
import uuid
from typing import Any
from redis.asyncio import Redis

class SessionManager:
    def __init__(self, redis: Redis, user_id: int):
        self.redis = redis
        self.user_id = user_id

    def _key(self, session_id: str) -> str:
        """
        生成会话键名，格式为 ai:session:{user_id}:{session_id}。
        """
        return f"ai:session:{self.user_id}:{session_id}"

    async def load_messages(self, session_id: str | None) -> tuple[str, list[dict[str, Any]]]:
        """
        返回 (session_id, messages列表)，messages 不包含 system prompt。
        如果 session_id 不存在，则创建新会话并立即写入 Redis 占位，防止中途异常丢失 session_id。
        """
        if session_id is None:
            # 生成新会话ID并立即保存空消息（占位），防止后续异常导致 session_id 失效
            session_id = str(uuid.uuid4())
            messages: list[dict[str, Any]] = []
            await self.save_messages(session_id, messages)
        else:
            key = self._key(session_id)
            raw = await self.redis.get(key)
            if raw:
                messages = json.loads(raw)
            else:
                # 没找到会话记录，当作新会话
                messages = []
                await self.save_messages(session_id, messages)
        return session_id, messages

    async def save_messages(self, session_id: str, messages: list[dict[str, Any]], ttl: int = 3600) -> None:
        """
        保存 messages,并设置过期时间。
        """
        key = self._key(session_id)
        _ = await self.redis.set(key, json.dumps(messages, ensure_ascii=False), ex=ttl)

    async def delete_session(self, session_id: str) -> None:
        key = self._key(session_id)
        _ = await self.redis.delete(key)