# utils/jwt_utils.py
"""JWT 工具：签发与校验 access token。

payload 约定：
    - sub: 用户 ID（字符串形式，符合 JWT 标准）
    - exp: 过期时间（UTC）
    - iat: 签发时间（UTC）
    - 其他业务 claim 可通过 extra_claims 注入
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException

_secret_key = os.getenv("JWT_SECRET_KEY")
if not _secret_key:
    raise ValueError("未设置 JWT_SECRET_KEY 环境变量，请检查 .env 文件或系统环境")
# 密钥
SECRET_KEY: str = _secret_key  # 显式标注 str，避免类型检查器收窄为 str | None

# 指定加密算法
ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")  # 默认 HS256
# 指定过期时长，默认 30 分钟
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def create_access_token(user_id: int, extra_claims: dict[str, str] | None = None) -> str:
    """签发 JWT。返回字符串形式的 token。"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)    # 签发 JWT


def decode_access_token(token: str) -> dict[str, Any]:
    """校验并解码 JWT。失败时抛出 401 HTTPException。"""
    try:
        # 校验 JWT（签名 + 过期），通过后返回payload 字典
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token 无效")