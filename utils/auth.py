# utils/auth.py
"""鉴权依赖：从 Authorization: Bearer <jwt> 提取并校验 JWT，返回当前登录的 user_id。"""
from typing import Annotated
from redis.asyncio import Redis
import json
from config.redis_config import get_redis

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from config.db_config import AsyncSessionLocal

from models.users import User
from utils.jwt_utils import decode_access_token

# FastAPI 自动从 Authorization: Bearer <token> 提取 credentials
security_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)],
) -> User:
    """校验 JWT 并返回用户对象，同时验证 token_version
    同时判断用户是否存在，若不存在则抛出 404 HTTPException
    """
    payload = decode_access_token(credentials.credentials)
    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=401, detail="Token 缺少 sub 字段")

    token_version = payload.get("version", 0)

    try:
        user_id = int(user_id_raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的用户标识")

    # 短生命周期会话，查询后立即关闭
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        if user.token_version != token_version:
            raise HTTPException(status_code=401, detail="Token 已失效，请重新登录")

        return user