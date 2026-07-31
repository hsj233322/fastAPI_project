# routers/internship.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from crud import internship as crud_internship
from config.db_config import get_db
from schemas import ApiResponse
from schemas.internship import (
    CategoryResponse,
    PaginatedInternshipResponse,
    InternshipListItemResponse,
    InternshipDetailResponse,
    RelatedInternshipResponse,
)
from services.cache_service import CacheService
from dependencies import get_cache
from services.view_counter_service import ViewCounterService
from dependencies import get_view_counter

router = APIRouter(prefix="/api/internship", tags=["实习岗位"])

@router.get("/categories", response_model=ApiResponse[list[CategoryResponse]])
async def get_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache)],
):
    cache_key = "internship:categories:list"

    categories = await cache.get_list(cache_key, CategoryResponse)
    if categories:
        print("命中redis缓存")
        return ApiResponse(data=categories)

    print("未命中redis缓存, 查询数据库")
    categories_orm = await crud_internship.get_categories(db)

    categories_pydantic = [CategoryResponse.model_validate(cat) for cat in categories_orm]

    if categories_pydantic:
        _ =await cache.set(cache_key, categories_pydantic, ttl=86400)   # 有数据，24小时
    else:
        _ =await cache.set(cache_key, [], ttl=60)   # 空数据缓存60秒，防止穿透

    return ApiResponse(data=categories_pydantic)


@router.get("/list", response_model=ApiResponse[PaginatedInternshipResponse])
async def get_internship_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: Annotated[int | None, Query(alias="categoryId")] = None,
    province: Annotated[str | None, Query()] = None,
    education: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(gt=0, le=100, alias="pageSize")] = 10,
):
    offset = (page - 1) * page_size

    items = await crud_internship.get_internship_list(
        db, category_id=category_id, province=province, education=education,
        skip=offset, limit=page_size
    )
    total = await crud_internship.get_internship_count(
        db, category_id=category_id, province=province, education=education
    )
    has_more = (offset + len(items)) < total

    internship_items = [InternshipListItemResponse.model_validate(i) for i in items]

    paginated = PaginatedInternshipResponse(
        items=internship_items,
        total=total,
        has_more=has_more,
    )
    return ApiResponse(data=paginated)


@router.get("/detail", response_model=ApiResponse[InternshipDetailResponse])
async def get_internship_detail(
    internship_id: Annotated[int, Query(alias="id")],
    db: Annotated[AsyncSession, Depends(get_db)],
    view_counter: Annotated[ViewCounterService, Depends(get_view_counter)],
):
    internship = await crud_internship.get_internship_detail(db, internship_id)
    if not internship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")

    # 异步记录浏览（异步计数）
    await view_counter.record_view(internship.id)
    pending = await view_counter.get_pending_views(internship.id)

    detail = InternshipDetailResponse.model_validate(internship)
    detail.views = internship.views + pending

    related = await crud_internship.get_related_internships(
        db, current_id=internship.id, category_id=internship.category_id
    )
    detail.related_internships = [
        RelatedInternshipResponse.model_validate(r) for r in related
    ]

    return ApiResponse(data=detail)