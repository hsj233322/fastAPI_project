# scripts/embed_jobs_from_csv.py
import asyncio
import numpy as np
import pandas as pd
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sentence_transformers import SentenceTransformer
import os
from sqlalchemy.ext.asyncio import AsyncEngine

# ========== 配置区 ==========
CSV_PATH = "ncss_intern_jobs_20260718_120440.csv"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://myuser:123456@localhost:3306/internship_app?charset=utf8mb4")
INDEX_NAME = "idx:jobs"
EMBEDDING_DIM = 512
BATCH_SIZE = 50     # 每批处理50条
# ============================

# 异步数据库引擎
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)

async def load_mysql_id_map() -> dict[str, int]:
    """
    加载 MySQL 中 position_id -> 自增id 的映射。

    向量检索结果需要回链 MySQL（前端点击推荐卡片按自增 id 查岗位详情），
    而 Redis 里原本只存了 CSV 的职位ID（字符串），无法直接转成自增 id。
    """
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, position_id FROM internship"))
        rows = result.all()

        clean_map = {}
        # 清洗 position_id，确保是字符串且去空格
        for row in rows:
            key = str(row.position_id).strip()  # 确保转字符串并去空格

            if key in clean_map:
                print(f"警告: position_id '{key}' 重复，将覆盖旧值 ID {clean_map[key]} -> {row.id}")
            clean_map[key] = row.id
        return clean_map


async def create_index(redis: Redis):
    """创建redisSearch 搜索索引"""
    try:
        _ = await redis.execute_command(
            "FT.CREATE", INDEX_NAME, "ON", "HASH", "PREFIX", "1", "job:", "SCHEMA",
            "job_id", "TAG", "SORTABLE",
            "province", "TAG", "SEPARATOR", ",",
            "education", "TAG", "SEPARATOR", ",",
            "embedding", "VECTOR", "HNSW", "6", "DIM", str(EMBEDDING_DIM), 
            "TYPE", "FLOAT32", "DISTANCE_METRIC", "COSINE"
        )
        print(f"索引 {INDEX_NAME} 创建成功")
    except Exception as e:
        if "Index already exists" in str(e):
            print("索引已存在，跳过创建")
        else:
            raise e

            
def parse_salary_range(salary_str) -> tuple[str, str]:
    """
    将 '6.0-8.0' 这样的月薪范围解析为 (下限, 上限) 字符串；
    缺失或形如 '-' 时返回 ('', '')，统一以字符串写入 Redis 哈希。
    """
    if salary_str is None:
        return "", ""
    s = str(salary_str).strip()
    if not s or s == "-":
        return "", ""
    parts = s.split("-")
    if len(parts) == 2:
        try:
            return str(int(float(parts[0]))), str(int(float(parts[1])))
        except ValueError:
            return "", ""
    return "", ""


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    对原始 CSV 数据进行清洗和预处理
    1. 填充所有 NaN 为空字符串
    2. 从“月薪范围(k)”解析出薪资下限/上限（转为字符串，避免存 Redis 报错）
    """
    df = df.fillna('')
    salaries = df['月薪范围(k)'].apply(parse_salary_range)
    df['薪资下限'] = salaries.apply(lambda pair: pair[0])
    df['薪资上限'] = salaries.apply(lambda pair: pair[1])

    return df

async def main():
    redis = None    # 占位,保证redis确实创建了连接才关闭，没有创建则跳过。
    try:
        # 加载模型
        print("正在加载 Embedding 模型...")
        model = SentenceTransformer(MODEL_NAME)
        print("模型加载完成")

        # 连接 Redis并创建索引
        redis = Redis.from_url(REDIS_URL, decode_responses=True)
        await create_index(redis)

        # 读取 CSV
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')

        # 数据清洗
        df = prepare_dataframe(df)
        print(f"共读取 {len(df)} 条岗位记录")

        # 加载 MySQL 的 position_id -> 自增id 映射
        id_map = await load_mysql_id_map()

        # 分批生成向量
        total = len(df)
        for start in range(0, total, BATCH_SIZE):
            end = min(start + BATCH_SIZE, total) 
            batch_df = df.iloc[start:end]

            batch_texts = [
                f"工作地点：{row.省份}。岗位名称：{row.岗位名称}。专业要求：{row.专业要求}。福利：{row.福利标签}。单位：{row.单位名称}。"
                for row in batch_df.itertuples()
            ]

            # 批量编码，转换为 numpy 数组
            embeddings = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=True)
            
            # 存储到 Redis 哈希表
            pipe = redis.pipeline()
            for idx, row in enumerate(batch_df.itertuples()):
                job_id = row.职位ID
                emb_bytes = embeddings[idx].astype(np.float32).tobytes()
                
                key = f"job:{job_id}"
                _ = pipe.hset(
                    key,
                    mapping={
                        "job_id": str(job_id),
                        "mysql_id": id_map.get(str(job_id), ""), 
                        "province": row.省份,
                        "education": row.学历要求,
                        "title": row.岗位名称,
                        "company": row.单位名称,
                        "salary_min": row.薪资下限,
                        "salary_max": row.薪资上限,
                        "embedding": emb_bytes,
                    }
                )
            await pipe.execute()
            print(f"已存储 {end}/{total} 条")
        print("所有岗位向量化完成！")
    except Exception as e:
        print(f"发生错误: {e}")
        raise
    finally:
        if redis:
            print("关闭 Redis 连接...")
            await redis.close()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())