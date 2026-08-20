# scripts/embed_jobs_from_csv.py
import asyncio
import numpy as np
import pandas as pd
from redis.asyncio import Redis
from sentence_transformers import SentenceTransformer
import os
import json

# ========== 配置区 ==========
CSV_PATH = "ncss_intern_jobs_20260718_120440.csv"  # 改成你存放CSV的实际路径
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
INDEX_NAME = "idx:jobs"
EMBEDDING_DIM = 384   # 与模型匹配
BATCH_SIZE = 50       # 每批处理50条
# ============================

async def create_index(redis: Redis):
    """创建Redis向量索引（如果不存在）"""
    try:
        # 注意：这里不再存储原文本，只存向量和关键过滤字段
        await redis.execute_command(
            f"FT.CREATE {INDEX_NAME} ON HASH PREFIX 1 job: SCHEMA "
            f"job_id TAG SORTABLE "
            f"province TAG SEPARATOR , "    # 用于按省份过滤
            f"education TAG SEPARATOR , "   # 用于按学历过滤
            f"embedding VECTOR HNSW 6 DIM {EMBEDDING_DIM} TYPE FLOAT32 DISTANCE_METRIC COSINE"
        )
        print(f"✅ 索引 {INDEX_NAME} 创建成功")
    except Exception as e:
        if "Index already exists" in str(e):
            print("ℹ️ 索引已存在，跳过创建")
        else:
            raise e

async def main():
    # 1. 加载模型（只加载一次，耗时约5秒）
    print("🚀 正在加载 Embedding 模型...")
    model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    print("✅ 模型加载完成")

    # 2. 连接 Redis
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await create_index(redis)

    # 3. 读取 CSV（pandas 自动处理编码）
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"📊 共读取 {len(df)} 条岗位记录")

    # 4. 准备文本列表（这就是你的“切片”拼接）
    texts = []
    for _, row in df.iterrows():
        # 将关键信息拼成一段话，让模型理解语义
        text = f"岗位名称：{row['岗位名称']}。专业要求：{row['专业要求']}。福利：{row['福利标签']}。单位：{row['单位名称']}。"
        texts.append(text)

    # 5. 分批生成向量（为了节省内存）
    total = len(df)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch_df = df.iloc[start:end]
        batch_texts = texts[start:end]

        # 批量编码（模型自动利用CPU多核）
        embeddings = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=True)
        
        # 存储到 Redis（使用 pipeline 批量提交，提高效率）
        pipe = redis.pipeline()
        for idx, (_, row) in enumerate(batch_df.iterrows()):
            job_id = row['职位ID']
            emb_bytes = embeddings[idx].astype(np.float32).tobytes()
            
            key = f"job:{job_id}"
            pipe.hset(
                key,
                mapping={
                    "job_id": str(job_id),
                    "province": row['省份'] or "",
                    "education": row['学历要求'] or "",
                    "embedding": emb_bytes,
                }
            )
        await pipe.execute()
        print(f"✅ 已存储 {end}/{total} 条")

    print("🎉 所有岗位向量化完成！")
    await redis.close()

if __name__ == "__main__":
    asyncio.run(main())