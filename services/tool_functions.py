# services/tool_functions.py
import logging
import re
import threading
from typing import Any

from pydantic import BaseModel, Field

from core.tool_context import ToolContext
from core.tool_registry import tool
import asyncio
import numpy as np
from config import SCORE_THRESHOLD, LOCATION_FILTER_THRESHOLD

logger = logging.getLogger(__name__)

# ===== 全局加载 Embedding 模型（常驻内存） =====
_embedding_model = None
_embedding_lock = threading.Lock()  # 防止并发初始化

# ===== 向量索引配置（与灌库脚本保持一致） =====
INDEX_NAME = "idx:jobs"
# 向量维度：bge-small-zh-v1.5 是 512 维
EMBEDDING_DIM = 512


def get_embedding_model():
    """获取全局加载的 embedding 模型"""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            # double-check，防止等待锁期间已经被其他线程初始化
            if _embedding_model is None:
                from sentence_transformers import SentenceTransformer
                _embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    return _embedding_model


# 省份后缀归一化（数据源中省份不带后缀，如 "河南"、"广东"）
_PROVINCE_SUFFIXES = ("维吾尔自治区", "回族自治区", "壮族自治区", "自治区", "特别行政区", "省", "市")


def _normalize_province(location: str) -> str | None:
    """将模型传入的地点归一化为数据源中的省份名，如 "河南省" -> "河南" """
    name = location.strip()
    for suffix in _PROVINCE_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)]
            break
    return name or None


# ===== 工具参数模型（Pydantic，同时用于生成 OpenAI schema 和运行时校验） =====
class SearchJobsBySemanticParams(BaseModel):
    query: str = Field(
        description="用户的核心需求描述（岗位方向、专业、技能、学历等），不要包含地点信息"
    )
    location: str | None = Field(
        default=None,
        description=(
            "期望的工作省份，如：河南、广东。"
            "用户提到工作地点时必传，城市需转换为所属省份（如郑州→河南、深圳→广东）；"
            "用户没有提到地点时省略此参数"
        ),
    )


@tool(
    name="search_jobs_by_semantic",
    description=(
        "根据用户的自然语言描述，通过语义匹配查找最相关的实习岗位，"
        "并支持通过 location 参数对工作省份做精确过滤。"
        "这是唯一用于搜索岗位的工具。无论用户是问'AI实习'、'广州的工作'还是'适合文科生的岗位'，都调用此工具。"
    ),
    params_model=SearchJobsBySemanticParams,
)
async def search_jobs_by_semantic_func(
    ctx: ToolContext,
    query: str,
    location: str | None = None,
    top_k: int = 5,
):
    """根据语义向量搜索实习岗位，返回岗位详情列表"""
    if not query or not query.strip():
        return []

    try:
        model = get_embedding_model()
        query_vec = await asyncio.to_thread(
            # 把查询文本编码成 512 维向量（numpy 数组）,并确保数据类型是 float32，和索引定义一致。
            lambda: model.encode(query, convert_to_numpy=True).astype(np.float32)
        )
        query_vec_bytes = query_vec.tobytes()   # 将 numpy 数组转成字节序列

        # 地域过滤条件：用户指定地点时，用 province TAG 精确过滤 + KNN 混合查询
        filter_expr = ""
        if location and location.strip():
            province = _normalize_province(location)
            # 仅接受常规省份名（中文/字母/数字），防止特殊字符破坏查询语法
            if province and re.fullmatch(r"\w+", province):
                filter_expr = f"(@province:{{{province}}})"

        # 1. 构造KNN 查询，直接要求返回所有需要的详情字段
        if filter_expr:
            q_str = f"{filter_expr}=>[KNN {top_k} @embedding $vec AS score]"
            # 地域是用户明确给出的硬性条件，此时语义分只负责排序，放宽阈值避免误杀
            threshold = LOCATION_FILTER_THRESHOLD
        else:
            q_str = f"*=>[KNN {top_k} @embedding $vec AS score]"
            threshold = SCORE_THRESHOLD

        from redis.commands.search.query import Query
        search = ctx.redis.ft(INDEX_NAME)
        q = (
            Query(q_str)
            .return_fields("mysql_id", "title", "company", "salary_min", "province", "education", "score")
            .dialect(2)
        )
        result = await search.search(q, query_params={"vec": query_vec_bytes})

        # 2. 过滤低分 + 直接构造结果
        result_list = []
        for doc in result.docs:
            try:
                score = float(getattr(doc, "score", "999"))
            except (ValueError, TypeError):
                score = 999.0

            if score > threshold:
                continue  # 分数太高，不相关，跳过

            try:
                job_id = int(getattr(doc, "mysql_id", "") or 0)
            except (ValueError, TypeError):
                continue
            if job_id <= 0:
                continue

            result_list.append({
                "id": job_id,
                "title": getattr(doc, "title", ""),
                "company_name": getattr(doc, "company", ""),
                "province": getattr(doc, "province", ""),
                "education": getattr(doc, "education", ""),
                "salary_min": getattr(doc, "salary_min", ""),
            })

        return result_list

    except Exception as e:
        logger.error(f"语义搜索失败: {e}")
        return []
