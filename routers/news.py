from fastapi import APIRouter, Depends, Query, HTTPException
from crud import news
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from typing import Annotated

# 创建 APIRuter 实例
router = APIRouter(prefix='/api/news',tags=["news"])
# prefix 是公共的url前缀，会自动补全下面所有的路由方法中的url，不需要再重复写

@router.get("/categories")  # 这里的url相当于/api/news/categories
async def get_categories(skip: int=0, limit: int=100, db: AsyncSession = Depends(get_db)):

    categories = await news.get_categories(db, skip, limit)

    return {
        "code": 200,
        "message": "success",
        "data": categories
    }

@router.get("/list")
async def get_news(
    category_id: Annotated[int, Query(alias="categoryId")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(gt=0, le=100, alias="pageSize")] = 10,
    db : AsyncSession = Depends(get_db)
):
    # 先处理分页规则 → 查询新闻列表（数据库操作） → 计算总量（数据库操作） → 计算是否还有更多
    offset =  (page-1)* page_size
    news_list = await news.get_news_list(db, category_id, offset, page_size)
    
    total = await news.get_news_count(db, category_id)

    has_more = (offset + len(news_list)) < total
    
    return {
        "code": 200,
        "message": "获取新闻列表成功",
        "data": {
            "list": news_list,
            "total": total,
            "hasMore": has_more
        }
    }

@router.get("/detail")
async def get_news_datail(news_id: Annotated[int, Query(alias="id")], db: AsyncSession = Depends(get_db)):

    # 获取新闻详情 + 浏览量+1 + 相关新闻
    news_detail = await news.get_news_detail(db, news_id)

    if not news_detail:
        raise HTTPException(status_code=404, detail="新闻不存在")

    views_res = await news.increase_news_views(db, news_detail.id)

    if not views_res:
        raise HTTPException(status_code=404, detail="新闻不存在")

    return {
        "code": 200,
        "message": "success",
        "data":{
            "id": news_detail.id,
            "title": news_detail.title,
            "content": news_detail.content,
            "image": news_detail.image,
            "author": news_detail.author,
            "publishTime": news_detail.publish_time,
            "categoryId": news_detail.category_id,
            "views": news_detail.views,
            "relatedNews": [] 
        }
    }