# dependencies.py
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession
from typing import Annotated

from config.redis_config import get_redis_client,  get_redis 
from services.cache_service import CacheService
from services.view_counter_service import ViewCounterService

# 全局单例
_view_counter: ViewCounterService | None = None

def get_view_counter_service() -> ViewCounterService:
    """获取全局单例（供 lifespan 和依赖注入共同使用）"""
    global _view_counter
    if _view_counter is None:
        # lifespan 中不能用 Depends，所以这里手动构造
        redis_client = get_redis_client()
        cache = CacheService(redis_client)
        _view_counter = ViewCounterService(cache)
    return _view_counter


async def start_background_tasks(session_factory: async_sessionmaker[AsyncSession]):
    """启动所有后台任务"""
    vc = get_view_counter_service()
    await vc.start_flush_loop(session_factory)
    print("浏览量刷库任务已启动")


async def stop_background_tasks():
    global _view_counter
    if _view_counter:
        await _view_counter.stop()
        _view_counter = None
        # 移到 stop() 之后，避免 stop 失败时仍显示成功
        print("浏览量刷库任务已停止")

# --- 路由依赖注入函数 ---
async def get_cache(redis: Annotated[Redis, Depends(get_redis)]) -> CacheService:
    return CacheService(redis)

async def get_view_counter(
) -> ViewCounterService:
    # 复用全局单例，保证路由和 lifespan 用的是同一个实例
    return get_view_counter_service()