import redis.asyncio as aioredis

RATE_LIMIT_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
if current > tonumber(ARGV[1]) then
    return 0
end
return 1
"""

async def check_rate_limit(redis: aioredis.Redis, key: str, max_requests: int, window_seconds: int) -> bool:
    """
    检查是否超过限流阈值
    返回 True 表示允许通过，False 表示触发限流
    """
    # 注册脚本，把字符串解析成 Redis 能懂的格式
    lua_script = redis.register_script(RATE_LIMIT_LUA)
    result = await lua_script(keys=[key], args=[max_requests, window_seconds])
    return bool(result)