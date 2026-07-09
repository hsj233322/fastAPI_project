# dependencies.py
from config.cache_service import CacheService
from config.redis_config import get_redis
from redis.asyncio import Redis
from fastapi import Depends

async def get_cache(redis: Redis = Depends(get_redis)) -> CacheService:
    return CacheService(redis)