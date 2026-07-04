# crud/collects.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.news import News, Category
from schemas.collects import CollectNewsInfo
from models.collects import Collect
from fastapi import HTTPException, status

async def get_user_collects(db: AsyncSession, user_id: int):
    """获取某用户的所有收藏新闻"""
    query = (
        select(
            News.id, 
            News.title, 
            News.image,
            Category.name.label("category_name"),   # 取别名
            Collect.created_at
        )
        .join(Collect, Collect.news_id == News.id)          # news ↔ collect
        .join(Category, Category.id == News.category_id)    # news ↔ category
        .where(Collect.user_id == user_id)                  # 过滤出当前用户的收藏
        .order_by(Collect.created_at.desc())                # 按收藏时间倒序
    )
    result = await db.execute(query)
    return result.mappings().all()


async def toggle_collect_news(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """切换收藏状态：如果已收藏则取消，如果未收藏则添加"""
    # 先查一下数据库里有没有这条收藏记录
    query = select(Collect).where(
        Collect.user_id == user_id, 
        Collect.news_id == news_id
    )
    result = await db.execute(query)
    existing_collect = result.scalar_one_or_none()
    
    # 如果存在，说明用户想“取消收藏”
    if existing_collect:
        await db.delete(existing_collect)
        await db.commit()
        return False # 返回 False 代表现在是“未收藏”状态
        
    # 如果不存在，说明用户想“添加收藏”
    else:
        # 严谨一点：可以先查一下这篇新闻存不存在
        news_exists = await db.get(News, news_id)
        if not news_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新闻不存在")
            
        new_collect = Collect(user_id=user_id, news_id=news_id)
        db.add(new_collect)
        await db.commit()
        return True # 返回 True 代表现在是“已收藏”状态