# utils/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from config.db_config import get_db
from models.users import User, UserToken

# 告诉FastAPI，要从 Header 的 Authorization: Bearer <token> 中提取数据
security_bearer = HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
        db: AsyncSession = Depends(get_db)
):
    """只要路由 Depends 了这个函数，就必须带 Token，否则直接返回 401。"""
    token = credentials.credentials

    # 去数据库查这个 Token 
    query = select(User).join(UserToken).where(
        UserToken.token == token,
        UserToken.expires_at > datetime.now(timezone.utc)
    )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # 没有找到用户，或者 Token 过期了，返回 401
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期，请重新登录",
        )
    
    # 找到了用户，返回用户信息
    return user