# utils/auth.py
"""鉴权依赖：从 Authorization: Bearer <jwt> 提取并校验 JWT，返回当前登录的 User 对象。"""
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from models.users import User
from utils.jwt_utils import decode_access_token

# FastAPI 自动从 Authorization: Bearer <token> 提取 credentials
security_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)],
) -> str:
    """JWT 鉴权依赖：校验 token 并返回当前登录用户信息字典。
    """
    # 校验 JWT（签名 + 过期），通过后返回payload 字典，失败时抛出 401 HTTPException
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token 缺少 sub 字段")
    # 返回 user_id
    return user_id
