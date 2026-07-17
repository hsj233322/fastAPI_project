# services/cache_service.py
import json
import logging
from typing import Any, Type, TypeVar
from redis.asyncio import Redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class CacheService:
    KEY_PREFIX: str = "myapp:v1:"  # 加版本号，方便后续缓存清理
    

    def __init__(self, redis: Redis):
        self._redis: Redis = redis

    def make_key(self, key: str) -> str:
        return f"{self.KEY_PREFIX}{key}"

    async def get(self, key: str, model: type[T]):
        """获取单个对象，自动反序列化为 Pydantic 模型"""
        try:
            raw = await self._redis.get(self.make_key(key))
            if raw is None:
                return None
            return model.model_validate_json(raw)  # 比 json.loads + model_validate 更快
        except Exception as e:
            logger.warning(f"Cache GET failed for {key}: {e}")
            return None  # 降级：返回 None，让调用方走 DB

    async def get_list(self, key: str, model: type[T]):
        """获取列表，自动反序列化"""
        try:
            raw = await self._redis.get(self.make_key(key))
            if raw is None:
                return None
            data = json.loads(raw)
            return [model.model_validate(item) for item in data]
        except Exception as e:
            logger.warning(f"Cache GET_LIST failed for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """写入缓存，自动序列化"""
        try:
            full_key = self.make_key(key)
            if isinstance(value, list):
                serialized = json.dumps([v.model_dump() if hasattr(v, 'model_dump') else v for v in value])
            elif isinstance(value, BaseModel):
                serialized = value.model_dump_json()
            else:
                serialized = json.dumps(value)
            
            _ =await self._redis.setex(full_key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache SET failed for {key}: {e}")
            return False  # 写入失败不影响主流程

    async def delete(self, key: str) -> bool:
        try:
            _ = await self._redis.delete(self.make_key(key))
            return True
        except Exception as e:
            logger.warning(f"Cache DELETE failed for {key}: {e}")
            return False
        
    async def incr(self, key: str, amount: int = 1):
        """原子自增，用于计数场景"""
        try:
            _ = await self._redis.incr(self.make_key(key), amount) 
            # 返回自增后的值
        except Exception as e:
            logger.warning(f"Cache INCR failed for {key}: {e}")
            return None

    async def get_int(self, key: str):
        """获取整数类型的缓存值"""
        try:
            raw = await self._redis.get(self.make_key(key))
            return int(raw) if raw is not None else None
        except Exception as e:
            logger.warning(f"Cache GET_INT failed for {key}: {e}")
            return None
        