# utils/rate_limit.py
"""基于 Redis 的通用频率限制工具

支持：
- 基于 IP 的限流（适用于所有接口）
- 基于用户/用户名的限流（适用于需要登录或注册的接口）
- 可配置的时间窗口和请求次数
"""
from fastapi import Request, HTTPException, status
from redis.asyncio import Redis

class RateLimiter:

    def __init__(self, key_prefix: str, max_requests: int, window_seconds: int):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def _make_key(self, *parts: str) -> str:
        """构建 Redis 限流 key"""
        return f"rate:{self.key_prefix}:" + ":".join(parts)

    async def check_ip(self, request: Request, redis: Redis) -> None:
        """
        基于客户端 IP 进行限流检查。
        超过限制时抛出 HTTPException(429)。
        """
        client_ip = request.client.host if request.client else "unknown"
        rate_key = self._make_key(f"ip:{client_ip}")
        await self._increment_and_check(redis, rate_key)

    async def check(self, request: Request, redis: Redis, identifier: str = "") -> None:
        """
        基于 IP + 标识符（如用户名）进行双重限流检查。
        会同时检查 IP 和 IP+identifier 两个维度。
        """
        client_ip = request.client.host if request.client else "unknown"

        # 1. 检查纯 IP 限流
        ip_key = self._make_key(f"ip:{client_ip}")
        await self._increment_and_check(redis, ip_key)

        # 2. 如果有 identifier，检查 IP + identifier 组合限流
        if identifier:
            combo_key = self._make_key(f"ip:{client_ip}", f"id:{identifier}")
            await self._increment_and_check(redis, combo_key)

    async def _increment_and_check(self, redis: Redis, key: str) -> None:
        """
        原子计数并检查是否超限。
        
        使用 SET NX 原子操作确保首次请求的计数和过期时间设置是原子的，
        避免 incr + expire 分离导致的 key 永不过期问题。
        """
        # 尝试原子设置初始值（仅首次请求生效）
        # SET key 1 EX window_seconds NX
        # NX: 仅当 key 不存在时设置，返回 True
        # EX: 过期时间，单位秒
        is_first = await redis.set(key, 1, ex=self.window_seconds, nx=True)
        
        if is_first:
            # 首次请求，计数为 1，已通过 SET NX 原子设置好过期时间
            count = 1
        else:
            # 后续请求，key 已存在，原子自增
            count = await redis.incr(key)
        
        if count > self.max_requests:
            ttl = await redis.ttl(key)
            wait_msg = f"{ttl} 秒后再试" if ttl > 0 else "稍后再试"
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请{wait_msg}",
            )


# ==================== 预设的限流器 ====================

# 登录限流：IP 维度 30秒5次，IP+用户名维度 30秒3次
login_limiter = RateLimiter(
    key_prefix="login",
    max_requests=5,
    window_seconds=30,
)

# 注册限流：仅 IP 维度 60秒3次
register_limiter = RateLimiter(
    key_prefix="register",
    max_requests=3,
    window_seconds=60,
)
