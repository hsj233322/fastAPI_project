# crud/historys.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.historys import ViewHistory
from models.news import News, Category
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import delete

async def add_view_history(db: AsyncSession, user_id: int, news_id: int):
    """记录浏览历史（存在则更新时间，不存在则插入）"""
    # 先查一下数据库里，这个用户有没有看过这篇新闻
    query = select(ViewHistory).where(
        ViewHistory.user_id == user_id, 
        ViewHistory.news_id == news_id
    )
    result = await db.execute(query)
    history_record  = result.scalar_one_or_none()
    
    # 如果以前看过，随便赋个值触发 onupdate
    if history_record:
        history_record.view_time = datetime.now(timezone.utc)
    else:
        # 如果没看过，插入一条新记录
        new_history = ViewHistory(user_id=user_id, news_id=news_id)
        db.add(new_history)
        
    await db.commit()

async def get_user_history(db: AsyncSession, user_id: int, limit: int = 20):
    """获取用户的浏览历史列表"""
    query = (
        select(
            ViewHistory.id,
            News.title,
            News.image,
            Category.category_name,
            ViewHistory.view_time
        )
        .join(News, ViewHistory.news_id == News.id)
        .join(Category, Category.id == News.category_id)
        .where(ViewHistory.user_id == user_id)
        .order_by(ViewHistory.view_time.desc()) # 按最后浏览时间倒序排列
        .limit(limit) # 限制条数，防止数据太多卡死
    )
    
    result = await db.execute(query)
    return result.all()

async def delete_one_history(db: AsyncSession, record_id: int, user_id: int):
    """删除单条浏览历史"""
    stmt = await db.get(ViewHistory, record_id)
    if not stmt or stmt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在或无权限")
    await db.delete(stmt)
    await db.commit()

async def delete_all_history(db: AsyncSession, user_id: int):
    """删除用户所有浏览历史"""
    stmt = delete(ViewHistory).where(ViewHistory.user_id == user_id)
    _ = await db.execute(stmt)
    await db.commit()