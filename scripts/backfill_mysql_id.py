# scripts/backfill_mysql_id.py
r"""
一次性回填脚本：给 Redis 中 job:{position_id} 哈希补写 mysql_id。

背景：
    embed_jobs_from_csv.py 会从 MySQL 加载 position_id -> 自增id 的映射来回填
    mysql_id；如果灌 Redis 时 MySQL 里还没有数据（顺序错了），所有 job 的
    mysql_id 都会是空字符串，导致语义搜索工具因 job_id <= 0 过滤掉全部结果。
    本脚本在 MySQL 已有数据后，重新把 mysql_id 写回 Redis，无需重建索引/重算向量。

用法（项目根目录执行）：
    python scripts/backfill_mysql_id.py

环境变量：
    DATABASE_URL  默认 mysql+aiomysql://myuser:123456@localhost:3306/internship_app?charset=utf8mb4
    REDIS_URL     默认 redis://localhost:6379/0
"""
import asyncio
import os

import aiomysql
from redis.asyncio import Redis

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://myuser:123456@localhost:3306/internship_app?charset=utf8mb4",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BATCH_SIZE = 200


def _parse_mysql_url(url: str) -> dict:
    """从 mysql+aiomysql://user:pwd@host:port/db 解析连接参数。"""
    # 去掉协议前缀
    body = url.split("://", 1)[1]
    # user:password@host:port/dbname
    creds, rest = body.rsplit("@", 1)
    user, password = creds.split(":", 1) if ":" in creds else (creds, "")
    host_port, dbname = rest.split("/", 1)
    if "?" in dbname:
        dbname = dbname.split("?", 1)[0]
    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        port = int(port)
    else:
        host, port = host_port, 3306
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "db": dbname,
        "charset": "utf8mb4",
    }


async def load_position_id_map(conn: aiomysql.Connection) -> dict[str, int]:
    """从 MySQL 加载 position_id -> 自增 id 的映射。"""
    async with conn.cursor() as cur:
        await cur.execute("SELECT id, position_id FROM internship")
        rows = await cur.fetchall()
    id_map: dict[str, int] = {}
    for row in rows:
        key = str(row[1]).strip()
        if key:
            id_map[key] = int(row[0])
    return id_map


async def main() -> None:
    db_cfg = _parse_mysql_url(DATABASE_URL)
    print(f"连接 MySQL: {db_cfg['host']}:{db_cfg['port']}/{db_cfg['db']}")
    conn = await aiomysql.connect(**db_cfg)
    try:
        id_map = await load_position_id_map(conn)
        print(f"MySQL internship 表共 {len(id_map)} 条 position_id 映射")
        if not id_map:
            print("!!! MySQL 里没有岗位数据，请先跑 import_data.py 灌库")
            return
    finally:
        conn.close()

    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis.ping()
        print(f"已连接 Redis: {REDIS_URL}")

        job_keys = [k async for k in redis.scan_iter(match="job:*", count=500)]
        print(f"Redis 中 job:* 数量: {len(job_keys)}")
        if not job_keys:
            print("!!! Redis 里没有岗位数据")
            return

        updated = 0
        not_found = 0
        pipe = redis.pipeline()
        for key in job_keys:
            position_id = key[len("job:"):]
            mysql_id = id_map.get(position_id)
            if mysql_id is None:
                not_found += 1
                continue
            pipe.hset(key, "mysql_id", str(mysql_id))
            updated += 1
            if updated % BATCH_SIZE == 0:
                await pipe.execute()
                pipe = redis.pipeline()
                print(f"已回填 {updated}/{len(job_keys)}")
        await pipe.execute()

        print(f"回填完成: 成功 {updated} 条，MySQL 中找不到对应 position_id 的 {not_found} 条")

        # 抽查
        print("抽查：")
        checked = 0
        async for key in redis.scan_iter(match="job:*", count=200):
            fields = await redis.hmget(key, "mysql_id", "province", "title")
            print(f"  {key}: mysql_id={fields[0]!r} province={fields[1]!r} title={fields[2]!r}")
            checked += 1
            if checked >= 3:
                break
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
