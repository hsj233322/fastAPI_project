from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.news import Category, News
from sqlalchemy import func, update


async def get_categories(db: AsyncSession, skip: int=0, limit: int=100):
    # 查询所有分类
    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_news_list(db: AsyncSession, category_id: int, skip: int=0, limit: int=10):
    # 查询指定分类下的所有新闻
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_news_count(db: AsyncSession, category_id: int):
    # 查询指定分类下的新闻数量
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()  # 只能有一个结果，否则报错

async def get_news_detail(db: AsyncSession, news_id: int) -> News | None:
    # 获取新闻详情
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def increase_news_views(db: AsyncSession, news_item: News) -> bool:
    """增加新闻浏览次数"""
    news_item.views += 1
    await db.commit()
    return True

async def get_related_news(db: AsyncSession, news_id: int, category_id: int, limit: int = 5):
    # 获取新闻的关联新闻
    stmt = select(News).where(
        News.id != news_id,
        News.category_id == category_id
    ).order_by(
        News.views.desc(),
        News.publish_time.desc()
    ).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()