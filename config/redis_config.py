# config/redis_config.py
import redis.asyncio as aioredis
from typing import AsyncGenerator
import os

# Redis 连接 URL (优先读取环境变量，如果没有则使用默认的本地 localhost)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建全局异步连接池
redis_pool = aioredis.ConnectionPool.from_url(
    REDIS_URL, 
    decode_responses=True,  
    max_connections=100       
)

# 获取 Redis 客户端实例
def get_redis_client() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)

# 用于 FastAPI 的 Depends() 依赖注入
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = get_redis_client()
    try:
        yield client
    finally:
        # 这里不需要 close，因为连接池会复用连接
        pass