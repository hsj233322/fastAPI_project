# routers/news.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from crud import news
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from typing import Annotated
from schemas import ApiResponse
from schemas.news import CategoryResponse, PaginatedNewsResponse, NewsListItemResponse, NewsDetailResponse, RelatedNewsResponse


# 创建 APIRuter 实例
router = APIRouter(prefix='/api/news',tags=["首页"])

# 获取新闻分类
@router.get("/categories", response_model=ApiResponse[list[CategoryResponse]])
async def get_categories(skip: int=0, limit: int=100, db: AsyncSession = Depends(get_db)):
    categories = await news.get_categories(db, skip, limit)
    return ApiResponse(data=categories)    

# 获取新闻列表
@router.get("/list",response_model=ApiResponse[PaginatedNewsResponse])
async def get_news(
    category_id: Annotated[int, Query(alias="categoryId")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(gt=0, le=100, alias="pageSize")] = 10,
    db : AsyncSession = Depends(get_db)
):
    # 处理分页规则
    offset =  (page-1)* page_size

    # 获取新闻列表
    news_list = await news.get_news_list(db, category_id, offset, page_size)

    # 获取新闻总数
    total = await news.get_news_count(db, category_id)

    # 判断是否有更多
    has_more = (offset + len(news_list)) < total
    
    news_items = [NewsListItemResponse.model_validate(item) for item in news_list]

    # 构造 PaginatedNews 对象
    paginated = PaginatedNewsResponse(
        item=news_items,
        total=total,
        has_more=has_more
    )

    return ApiResponse(data=paginated)

# 获取新闻详情
@router.get("/detail", response_model=ApiResponse[NewsDetailResponse])
async def get_news_detail(news_id: Annotated[int, Query(alias="id")], db: AsyncSession = Depends(get_db)):

    # 获取新闻详情
    news_detail = await news.get_news_detail(db, news_id)
    if not news_detail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新闻不存在")

    # 增加浏览量
    await news.increase_news_views(db, news_detail)

    # 获取相关新闻
    related = await news.get_related_news(db, news_detail.id, news_detail.category_id)

    news_detail_model = NewsDetailResponse.model_validate(news_detail) 
    news_detail_model.related_news = [
        RelatedNewsResponse.model_validate(item) for item in related
    ]

    return ApiResponse(data=news_detail_model)
