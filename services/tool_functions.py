# services/tool_functions.py
import json
import logging
import threading
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from redis.commands.search.query import Query
from types import SimpleNamespace
from crud.internship import search_internships
import os
from sentence_transformers import SentenceTransformer
import asyncio
import numpy as np
from config import SCORE_THRESHOLD

logger = logging.getLogger(__name__)

# ===== 全局加载 Embedding 模型（常驻内存） =====
_embedding_model = None
_embedding_lock = threading.Lock()  # 防止并发初始化

# ===== 向量索引配置（与灌库脚本保持一致） =====
INDEX_NAME = "idx:jobs"
# 向量维度：bge-small-zh-v1.5 是 512 维
EMBEDDING_DIM = 512


def _parse_ft_search_raw_result(raw: list[Any]) -> SimpleNamespace:
    """
    兜底：将 execute_command('FT.SEARCH', ...) 返回的原始 list 解析为
    与 redis-py search() 相同的访问格式（result.docs[i].get('field')）。

    FT.SEARCH 原始返回格式（RESP array）：
      [total_count, doc_id_1, [f1, v1, f2, v2, ...], doc_id_2, [f1, v1, ...], ...]
    """
    docs: list[SimpleNamespace] = []
    if not raw or len(raw) < 1:
        return SimpleNamespace(docs=docs, total=0)
    total = int(raw[0]) if isinstance(raw[0], (int, str, bytes)) else 0
    # 遍历 doc_id -> fields 对（从 index 1 开始，步长 2）
    i = 1
    while i + 1 < len(raw):
        _doc_id = raw[i]  # doc id 暂不使用
        fields_pairs = raw[i + 1]
        # fields_pairs 应该是 [f1, v1, f2, v2, ...]
        mapping: dict[str, str] = {}
        if isinstance(fields_pairs, (list, tuple)):
            for j in range(0, len(fields_pairs) - 1, 2):
                key = fields_pairs[j]
                val = fields_pairs[j + 1]
                if isinstance(key, bytes):
                    key = key.decode("utf-8", errors="ignore")
                if isinstance(val, bytes):
                    val = val.decode("utf-8", errors="ignore")
                mapping[str(key)] = str(val)
        # 用 SimpleNamespace + 自定义 get 方法，对齐接口
        ns = SimpleNamespace(**mapping)
        ns.get = lambda k, default=None, m=mapping: m.get(k, default)  # type: ignore[attr-defined]
        docs.append(ns)
        i += 2
    return SimpleNamespace(docs=docs, total=total)


async def search_jobs_func(
    db: AsyncSession,
    keyword: str | None = None,
    location: str | None = None,
    education: str | None = None,
    redis: Redis | None = None,  # 占位，保持接口一致性
    ) -> list[dict[str, Any]]:
    """根据条件搜索实习岗位，返回可序列化的字典列表"""
    jobs = await search_internships(
        db,
        keyword=keyword,
        location=location,
        education=education,
        limit=8,
    )
    result = []
    for job in jobs:
        result.append({
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "province": job.province,
            "education": job.education,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
        })
    return result


async def get_job_detail_func(db: AsyncSession, job_id: int, redis: Redis | None = None) -> dict[str, Any]:
    """根据岗位ID返回岗位详情"""
    from crud.internship import get_internship_by_id
    job = await get_internship_by_id(db, job_id)
    if not job:
        return {"error": "未找到该岗位"}
    return {
        "id": job.id,
        "title": job.title,
        "company_name": job.company_name,
        "province": job.province,
        "education": job.education,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "description": getattr(job, "description", ""),  # 如果有描述字段
    }

def get_embedding_model():
    """获取全局加载的 embedding 模型"""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            # double-check，防止等待锁期间已经被其他线程初始化
            if _embedding_model is None:
                _embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    return _embedding_model


async def search_jobs_by_semantic_func(
    redis: Redis,
    query: str, # 用户输入的自然语言查询
    top_k: int = 5,
):
    if not query or not query.strip():
        # 如果查询为空或只包含空白字符，直接返回空列表，避免无意义计算
        return []

    try:
        model = get_embedding_model()
        query_vec = await asyncio.to_thread(
            # 把查询文本编码成 512 维向量（numpy 数组）,并确保数据类型是 float32，和索引定义一致。
            lambda: model.encode(query, convert_to_numpy=True).astype(np.float32)   
        )
        query_vec_bytes = query_vec.tobytes()   # 将 numpy 数组转成字节序列（Redis 向量字段需要的格式），这就是要传给 Redis 的查询向量。
        
        # 1. 构造KNN 查询，直接要求返回所有需要的详情字段
        q_str = f"*=>[KNN {top_k} @embedding $vec AS score]"
        search = redis.ft(INDEX_NAME)
        q = (
            Query(q_str)
            .return_fields("job_id", "title", "company", "salary_min", "province", "education", "score")   # 指定返回的字段，包括 KNN 自动生成的 score
            .dialect(2)
        )
        result = await search.search(q, query_params={"vec": query_vec_bytes})  # 执行查询

        # 2. 过滤低分 + 直接构造结果
        result_list = []
        for doc in result.docs:
            try:
                score = float(doc.get("score", "999"))  # 从 Redis 返回的 doc 里取 score 字段，转换为浮点数，取不到就赋值为 999.0，避免 None 错误。
            except (ValueError, TypeError):
                score = 999.0
            
            if score > SCORE_THRESHOLD:
                continue  # 分数太高，不相关，跳过
                
            # 从 Redis 返回的 doc 里取数据
            result_list.append({
                "id": int(doc.get("job_id", 0)),
                "title": doc.get("title", ""),
                "company_name": doc.get("company", ""),
                "province": doc.get("province", ""),
                "education": doc.get("education", ""),
                "salary_min": doc.get("salary_min", ""),
            })
            
        return result_list

    except Exception as e:
        logger.error(f"语义搜索失败: {e}")
        return []