# crud/collects.py
from sqlalchemy import select, delete  # 这里增加了 delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.collects import Collect
from models.internship import Internship


async def add_collect(db: AsyncSession, user_id: int, internship_id: int):
    """添加收藏（重复收藏静默成功）"""
    exists = await db.execute(
        select(Collect).where(
            Collect.user_id == user_id,
            Collect.internship_id == internship_id,
        )
    )
    if exists.scalar_one_or_none():
        return  # 已经收藏

    db.add(Collect(user_id=user_id, internship_id=internship_id))
    await db.commit()


async def remove_collect(db: AsyncSession, user_id: int, internship_id: int):
    """取消收藏（不存在则404）"""
    stmt = await db.execute(
        select(Collect).where(
            Collect.user_id == user_id,
            Collect.internship_id == internship_id,
        )
    )
    record = stmt.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未收藏该岗位")
    await db.delete(record)
    await db.commit()


async def get_user_collects(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20
):
    """获取用户收藏列表，返回收藏记录与岗位信息"""
    query = (
        select(
            Collect.internship_id,
            Internship.title,
            Internship.category_id,  # 如果需要 category_name，再 join 分类表
            Collect.created_at,
        )
        .join(Internship, Collect.internship_id == Internship.id)
        .where(Collect.user_id == user_id)
        .order_by(Collect.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.all()


async def clear_user_collects(db: AsyncSession, user_id: int):
    """清空指定用户的所有收藏"""
    stmt = delete(Collect).where(Collect.user_id == user_id)
    await db.execute(stmt)
    await db.commit()