# routers/news.py
from fastapi import APIRouter, Depends, Query, HTTPException
from crud import news
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from typing import Annotated
from schemas.news import ApiResponse, Category, PaginatedNews, NewsDetail, RelatedNews


# 创建 APIRuter 实例
router = APIRouter(prefix='/api/news',tags=["news"])
# prefix 是公共的url前缀，会自动补全下面所有的路由方法中的url，不需要再重复写

# 获取新闻分类
@router.get("/categories", response_model=ApiResponse[list[Category]])
async def get_categories(skip: int=0, limit: int=100, db: AsyncSession = Depends(get_db)):
    categories = await news.get_categories(db, skip, limit)
    return ApiResponse(data=categories)    

# 获取新闻列表
@router.get("/list",response_model=ApiResponse[PaginatedNews])
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
    
    return ApiResponse(
        data={
            "list": news_list,  # ORM对象
            "total": total,
            "hasMore": has_more
        }
    )

# 获取新闻详情
@router.get("/detail", response_model=ApiResponse[NewsDetail])
async def get_news_detail(news_id: Annotated[int, Query(alias="id")], db: AsyncSession = Depends(get_db)):

    # 获取新闻详情
    news_detail = await news.get_news_detail(db, news_id)
    if not news_detail:
        raise HTTPException(status_code=404, detail="新闻不存在")

    # 增加浏览量
    success = await news.increase_news_views(db, news_detail.id)
    if not success:
        raise HTTPException(status_code=404, detail="新闻不存在")

    # 获取相关新闻
    related = await news.get_related_news(db, news_detail.id, news_detail.category_id)

    news_detail_model = NewsDetail.model_validate(news_detail) 
    news_detail_model.related_news = [
        RelatedNews.model_validate(item) for item in related
    ]

    return ApiResponse(data=news_detail_model)