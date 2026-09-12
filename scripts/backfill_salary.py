# scripts/backfill_salary.py
r"""
一次性回填脚本：给 Redis 中已有的 job:{position_id} 哈希补写 salary_max。

背景：
    早期 embed_jobs_from_csv.py 只写了 salary_min，且数据来自“月薪范围(k)”
    （如 '6.0-8.0'）。向量无需重算，本脚本只解析 CSV 的薪资范围并把
    salary_min / salary_max 两个字段以字符串写回哈希，RediSearch 可直接 RETURN
    哈希字段，无需重建索引。

用法（在能访问 Redis 的机器上，项目根目录执行）：
    # Linux / 云服务器（6379 已映射到宿主机）
    REDIS_URL=redis://localhost:6379/0 python scripts/backfill_salary.py

    # Windows PowerShell
    $env:REDIS_URL="redis://localhost:6379/0"; .venv\Scripts\python.exe scripts\backfill_salary.py

可选：
    CSV_PATH=ncss_intern_jobs_xxx.csv python scripts/backfill_salary.py
"""
import asyncio
import csv
import os

from redis.asyncio import Redis

CSV_PATH = os.getenv("CSV_PATH", "ncss_intern_jobs_20260718_120440.csv")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BATCH_SIZE = 200


def parse_salary_range(salary_str: str) -> tuple[str, str]:
    """'6.0-8.0' -> ('6', '8')；缺失/'-' -> ('', '')，与 import_data.parse_salary 口径一致。"""
    s = (salary_str or "").strip()
    if not s or s == "-":
        return "", ""
    parts = s.split("-")
    if len(parts) == 2:
        try:
            return str(int(float(parts[0]))), str(int(float(parts[1])))
        except ValueError:
            return "", ""
    return "", ""


async def main() -> None:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV 不存在: {CSV_PATH}（请在项目根目录执行或设置 CSV_PATH）")

    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis.ping()
        print(f"已连接 Redis: {REDIS_URL}")

        # 先读 CSV，避免连不上 Redis 时白做解析
        rows: list[tuple[str, str, str]] = []
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                lo, hi = parse_salary_range(row.get("月薪范围(k)", ""))
                rows.append((row["职位ID"], lo, hi))
        print(f"CSV 解析完成，共 {len(rows)} 条")

        updated = 0
        with_salary = 0
        pipe = redis.pipeline()
        for job_id, lo, hi in rows:
            if lo and hi:
                with_salary += 1
            pipe.hset(
                f"job:{job_id}",
                mapping={"salary_min": lo, "salary_max": hi},
            )
            updated += 1
            if updated % BATCH_SIZE == 0:
                await pipe.execute()
                pipe = redis.pipeline()
                print(f"已回填 {updated}/{len(rows)}")
        await pipe.execute()

        print(f"回填完成: {updated} 条（其中薪资完整 {with_salary} 条，缺失 {updated - with_salary} 条）")

        # 抽查 3 个 key 验证写入结果
        print("抽查：")
        checked = 0
        async for key in redis.scan_iter(match="job:*", count=200):
            fields = await redis.hmget(key, "salary_min", "salary_max", "title")
            print(f"  {key}: salary_min={fields[0]!r} salary_max={fields[1]!r} title={fields[2]!r}")
            checked += 1
            if checked >= 3:
                break
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
