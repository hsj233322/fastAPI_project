# utils/auth.py
"""鉴权依赖：从 Authorization: Bearer <jwt> 提取并校验 JWT，返回当前登录的 User 对象。"""
from typing import Annotated

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
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)],
) -> User:
    """JWT 鉴权依赖：校验 token 并返回当前登录用户。

    流程：
        1. 从 Header 提取 JWT
        2. 校验签名与过期（失败直接抛 401）
        3. 从 payload.sub 取出 user_id，回查数据库
           （回查是为了拿到最新的用户对象，便于后续业务直接使用）
    """
    # 1. 校验 JWT（签名 + 过期），失败时 decode_access_token 会抛 401
    payload = decode_access_token(credentials.credentials)

    # 2. 取出 user_id
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 缺少 sub 字段",
        )
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 内 sub 字段格式非法",
        )

    # 3. 回查数据库，确保用户存在（防止已注销用户继续使用旧 token）
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在，请重新登录",
        )

    return user
