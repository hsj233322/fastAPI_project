# services/view_counter_service.py
import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import async_sessionmaker
from services.cache_service import CacheService

logger = logging.getLogger(__name__)


class ViewCounterService:
    FLUSH_INTERVAL = 60
    KEY_BASE = "news:views"

    def __init__(self, cache: CacheService):
        self._cache = cache
        self._task: Optional[asyncio.Task] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._running = False

    def _raw_key(self, news_id: int) -> str:
        """返回不带前缀的原始 key，交给 CacheService 去加前缀"""
        return f"{self.KEY_BASE}:{news_id}"
    
    def _raw_pattern(self) -> str:
        """返回不带前缀的 scan pattern"""
        return f"{self.KEY_BASE}:*"

    # 获取某个新闻的未刷盘浏览量
    async def get_pending_views(self, news_id: int) -> int:
        return await self._cache.get_int(self._raw_key(news_id)) or 0

    async def record_view(self, news_id: int) -> None:
        # CacheService.incr 内部会调用 make_key 加前缀
        await self._cache.incr(self._raw_key(news_id))
    async def start_flush_loop(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())
        logger.info(f"ViewCounter flush loop started (interval={self.FLUSH_INTERVAL}s)")

    async def _flush_loop(self) -> None:
        while self._running:
            try:
                await self._flush_to_db()
            except Exception as e:
                logger.error(f"ViewCounter flush failed: {e}", exc_info=True)
            try:
                await asyncio.sleep(self.FLUSH_INTERVAL)
            except asyncio.CancelledError:
                logger.info("Flush loop sleep cancelled, exiting loop")
                break

    async def _flush_to_db(self) -> None:
        if not self._session_factory:
            logger.warning("No session_factory, skipping flush")
            return

        redis = self._cache._redis
        # flush 直接操作 redis，需要手动加前缀
        full_pattern = self._cache.make_key(self._raw_pattern())
        full_prefix = self._cache.KEY_PREFIX  # "myapp:v1:"
        cursor = 0
        updated = 0

        logger.debug(f"Scanning with pattern: {full_pattern}")

        while True:
            cursor, keys = await redis.scan(cursor, match=full_pattern, count=100)
            if not keys:
                if cursor == 0:
                    break
                continue

            pipe = redis.pipeline()
            for key in keys:
                pipe.getdel(key)
            values = await pipe.execute()

            async with self._session_factory() as db:
                from sqlalchemy import text
                for key, val in zip(keys, values):
                    if val is None:
                        continue
                    key_str = key.decode() if isinstance(key, bytes) else key
                    # 先去掉完整前缀，再提取 news_id
                    # key_str = "myapp:v1:news:views:123"
                    stripped = key_str[len(full_prefix):]  # "news:views:123"
                    news_id = int(stripped.rsplit(":", 1)[-1])  # "123"
                    delta = int(val)
                    if delta > 0:
                        await db.execute(
                            text("UPDATE news SET views = views + :delta WHERE id = :id"),
                            {"delta": delta, "id": news_id},
                        )
                        updated += 1
                await db.commit()

            if cursor == 0:
                break

        if updated:
            logger.info(f"ViewCounter flushed {updated} news views to DB")
        else:
            logger.debug("ViewCounter flush: no pending views found")

    async def stop(self) -> None:
        logger.info("ViewCounter stopping...")
        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._session_factory:
            try:
                logger.info("Executing final flush before shutdown...") 
                await self._flush_to_db()
                logger.info("Final flush completed successfully") 
            except Exception as e:
                logger.error(f"Final flush FAILED: {e}", exc_info=True)
        else:
            logger.warning("No session_factory available for final flush!") 