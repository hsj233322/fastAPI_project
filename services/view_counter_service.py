# services/view_counter_service.py
import asyncio
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from services.cache_service import CacheService
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ViewCounterService:
    FLUSH_INTERVAL: int = 60
    KEY_BASE: str = "internship:views"

    def __init__(self, cache: CacheService):
        self._cache: CacheService = cache
        self._task: asyncio.Task[None] | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._running: bool = False

    def _raw_key(self, internship_id: int) -> str:
        """返回不带前缀的原始 key，交给 CacheService 去加前缀"""
        return f"{self.KEY_BASE}:{internship_id}"
    
    def _raw_pattern(self) -> str:
        """返回不带前缀的 scan pattern"""
        return f"{self.KEY_BASE}:*"

    # 获取某个岗位尚未刷库的浏览量
    async def get_pending_views(self, internship_id: int) -> int:
        return await self._cache.get_int(self._raw_key(internship_id)) or 0

    # 记录一次浏览，Redis 原子自增
    async def record_view(self, internship_id: int) -> None:
        # CacheService.incr 内部会调用 make_key 加前缀
        await self._cache.incr(self._raw_key(internship_id))
        
    # 启动后台刷库循环
    async def start_flush_loop(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())
        logger.info(f"ViewCounter flush loop started (interval={self.FLUSH_INTERVAL}s)")

    # 后台刷库循环
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

    # 从 redis 刷盘浏览量到数据库
    # 每个循环最多处理 100 个 key
    # 每个 key 对应的浏览量 delta 为整数
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
            if cursor == 0:
                break
            if not keys:
                continue

            # ---------- 1. 从 Redis 取出数据并删除键 ----------
            pipe = redis.pipeline()
            for key in keys:
                _ = pipe.getdel(key)
            values = await pipe.execute()

            # ---------- 2. 构建批量更新参数 ----------
            params = []
            for key, val in zip(keys, values):
                if val is None: # 键不存在，跳过
                    continue
                delta = int(val)
                if delta <= 0: # 浏览量非正数，跳过
                    continue
                # 提取 internship_id
                key_str = key.decode() if isinstance(key, bytes) else key
                stripped = key_str[len(full_prefix):]          # "internship:views:123"
                internship_id = int(stripped.rsplit(":", 1)[-1])  # 123
                params.append({"delta": delta, "id": internship_id})

            # ---------- 3. 尝试批量更新 MySQL ----------
            if params:
                async with self._session_factory() as db:
                    try:
                        # 一次 executemany 发送所有更新
                        _ = await db.execute(
                            text("UPDATE internship SET views = views + :delta WHERE id = :id"),
                            params  # 列表，SQLAlchemy 自动 executemany
                        )
                        await db.commit()
                        updated += len(params)   # 只有全部成功才计数
                    except Exception as e:
                        # MySQL 更新或提交失败（网络/死锁/宕机）
                        logger.error(f"MySQL更新失败，批次大小={len(params)}，错误: {e}")
                        # ---------- 4. 写回 Redis ----------
                        restore_pipe = redis.pipeline()
                        # 跳过 None 值，避免回写失败
                        for key, val in zip(keys, values):
                            if val is not None:
                                # 用 incrby 回写，避免直接 set 时的原子性问题
                                restore_pipe.incrby(key, int(val)) 
                        await restore_pipe.execute()
                        # 这一批数据已经回到 Redis，下一次 scan 还会取出，无需额外处理

            # ---------- 5. 游标判断 ----------
            if cursor == 0:
                break

        if updated:
            logger.info(f"ViewCounter flushed {updated} internship views to DB")
        else:
            logger.debug("ViewCounter flush: no pending views found")

    # 停止刷库循环，并做最后一次刷库
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