# routers/news.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from crud import news
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from typing import Annotated
from schemas import ApiResponse
from schemas.news import CategoryResponse, PaginatedNewsResponse, NewsListItemResponse, NewsDetailResponse, RelatedNewsResponse
from services.cache_service import CacheService
from dependencies import get_cache
from services.view_counter_service import ViewCounterService
from dependencies import get_view_counter

# 创建 APIRuter 实例
router = APIRouter(prefix='/api/news',tags=["新闻模块"])

# 获取新闻分类
@router.get("/categories", response_model=ApiResponse[list[CategoryResponse]])
async def get_categories(
    db: Annotated[AsyncSession, Depends(get_db)], 
    cache: Annotated[CacheService, Depends(get_cache)],
):
    cache_key = "news:categories:list"

    # 读取Redis缓存 + 反序列化 + 异常降级
    categories = await cache.get_list(cache_key, CategoryResponse)
    if categories:
        print("命中redis缓存")
        return ApiResponse(data=categories)

    # 缓存中没有，则从数据库中获取
    print("未命中redis缓存, 查询数据库")
    categories_orm = await news.get_categories(db)

    # 转换为 Pydantic 模型
    categories_pydantic = [CategoryResponse.model_validate(cat) for cat in categories_orm]

    # 序列化 + 写入Redis
    _ = await cache.set(cache_key, categories_pydantic, ttl=86400)  # 分类几乎不变，所以缓存时间可以设的久一些

    return ApiResponse(data=categories_pydantic)    

# 获取新闻列表
@router.get("/list",response_model=ApiResponse[PaginatedNewsResponse])
async def get_news(
    db : Annotated[AsyncSession, Depends(get_db)],
    category_id: Annotated[int, Query(alias="categoryId")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(gt=0, le=100, alias="pageSize")] = 10,
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
async def get_news_detail(
    news_id: Annotated[int, Query(alias="id")], 
    db: Annotated[AsyncSession, Depends(get_db)],
    view_counter: Annotated[ViewCounterService, Depends(get_view_counter)]      
):
    news_detail = await news.get_news_detail(db, news_id)
    if not news_detail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新闻不存在")

    await view_counter.record_view(news_detail.id)

    pending = await view_counter.get_pending_views(news_detail.id)
    
    news_detail_model = NewsDetailResponse.model_validate(news_detail)
    news_detail_model.views = news_detail.views + pending

    related = await news.get_related_news(db, news_detail.id, news_detail.category_id)
    news_detail_model.related_news = [
        RelatedNewsResponse.model_validate(item) for item in related
    ]

    return ApiResponse(data=news_detail_model)