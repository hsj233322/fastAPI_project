# scripts/diag_redis_jobs.py
r"""
Redis 岗位数据诊断脚本。检查 job:* 哈希的关键字段，定位"查不到岗位"的根因。

用法：
    python scripts/diag_redis_jobs.py
    REDIS_URL=redis://localhost:6379/0 python scripts/diag_redis_jobs.py
"""
import asyncio
import os
from collections import Counter

from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
INDEX_NAME = "idx:jobs"


async def main() -> None:
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        print(f"PING -> {await redis.ping()}")
        print(f"DB size: {await redis.dbsize()}")

        # 1. 统计 job:* 的数量和字段完整度
        job_keys = [k async for k in redis.scan_iter(match="job:*", count=500)]
        print(f"\njob:* 数量: {len(job_keys)}")

        if not job_keys:
            print("!!! Redis 里没有任何岗位数据，需要先跑灌库脚本")
            return

        missing_mysql = 0
        missing_province = 0
        missing_salary_max = 0
        provinces = Counter()
        total = 0

        pipe = redis.pipeline()
        for k in job_keys:
            pipe.hmget(k, "mysql_id", "province", "salary_max", "title")
        all_fields = await pipe.execute()

        for k, fields in zip(job_keys, all_fields):
            total += 1
            mysql_id, province, salary_max, title = fields
            if not mysql_id:
                missing_mysql += 1
            if not province:
                missing_province += 1
            if not salary_max:
                missing_salary_max += 1
            provinces[province or "(空)"] += 1

        print(f"\n字段缺失统计（共 {total} 条）:")
        print(f"  mysql_id 为空: {missing_mysql}  {'<<< 会导致工具过滤掉所有结果' if missing_mysql else ''}")
        print(f"  province 为空: {missing_province}")
        print(f"  salary_max 为空: {missing_salary_max}")

        print(f"\n河南岗位数: {provinces.get('河南', 0)}")
        print(f"省份分布 top10:")
        for p, c in provinces.most_common(10):
            print(f"  {p!r}: {c}")

        # 2. 抽查 3 个完整 job 的全部字段
        print("\n抽查 3 个 job 的完整字段:")
        for k in job_keys[:3]:
            fields = await redis.hgetall(k)
            print(f"  {k}:")
            for fk, fv in fields.items():
                if fk == "embedding":
                    print(f"    {fk}: <{len(fv)} bytes>")
                else:
                    print(f"    {fk}: {fv!r}")

        # 3. 尝试用河南做一次 RediSearch 查询
        try:
            from redis.commands.search.query import Query
            search = redis.ft(INDEX_NAME)
            # 只查 province，不做 KNN，看能不能命中
            q = Query("@province:{河南}").return_fields("title", "province").dialect(2)
            res = await search.search(q)
            print(f"\nRediSearch 纯省份查询 '@province:{{河南}}' 命中: {res.total} 条")
            for doc in res.docs[:3]:
                print(f"  - {getattr(doc, 'title', '')} (province={getattr(doc, 'province', '')})")
        except Exception as e:
            print(f"\nRediSearch 查询失败: {type(e).__name__}: {e}")

    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
