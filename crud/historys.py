# crud/historys.py
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.historys import ViewHistory
from models.internship import Internship


async def add_view_history(db: AsyncSession, user_id: int, internship_id: int):
    """记录浏览历史（存在则更新时间，不存在则插入）"""
    query = select(ViewHistory).where(
        ViewHistory.user_id == user_id,
        ViewHistory.internship_id == internship_id,
    )
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if record:
        record.view_time = datetime.now()
    else:
        record = ViewHistory(user_id=user_id, internship_id=internship_id)
        db.add(record)

    await db.commit()


async def get_user_history(db: AsyncSession, user_id: int, limit: int = 20):
    """获取用户浏览历史列表"""
    query = (
        select(
            ViewHistory.id,
            Internship.id.label("internship_id"),
            Internship.title,
            Internship.company_name,
            ViewHistory.view_time,
        )
        .join(Internship, ViewHistory.internship_id == Internship.id)
        .where(ViewHistory.user_id == user_id)
        .order_by(ViewHistory.view_time.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.all()


async def delete_one_history(db: AsyncSession, record_id: int, user_id: int):
    """删除单条浏览历史"""
    stmt = await db.get(ViewHistory, record_id)
    if not stmt or stmt.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记录不存在或无权限",
        )
    await db.delete(stmt)
    await db.commit()


async def delete_all_history(db: AsyncSession, user_id: int):
    """清空用户所有浏览历史"""
    stmt = delete(ViewHistory).where(ViewHistory.user_id == user_id)
    
    _ = await db.execute(stmt)
    await db.commit()