# services/tool_functions.py
import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from crud.internship import search_internships


async def search_jobs_func(
    db: AsyncSession,
    keyword: str | None = None,
    location: str | None = None,
    education: str | None = None,
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


async def get_job_detail_func(db: AsyncSession, job_id: int) -> dict[str, Any]:
    """根据岗位ID返回岗位详情"""
    # 你需要自己实现一个根据 id 查询岗位的函数，比如：
    # job = await get_internship_by_id(db, job_id)
    # 下面先假设有这样一个函数，如果没有就写一个
    from crud.internship import get_internship_by_id  # 你需要有这个函数
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