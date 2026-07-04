# routers/collects.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from utils.auth import get_current_user
from models.users import User
from schemas.news import ApiResponse
from schemas.collects import CollectNewsInfo
from crud.collects import get_user_collects, toggle_collect_news


router = APIRouter(prefix="/api/collects", tags=["新闻收藏"])

""" 获取我的收藏列表"""
@router.get("/list", response_model=ApiResponse[list[CollectNewsInfo]])
async def get_my_collects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user) # 必须登录才能看自己的收藏
):
    # 调用 CRUD 层获取数据（这里可以复用查询新闻的逻辑）
    collects_list = await get_user_collects(db, user.id)
    return ApiResponse(data=collects_list)

""" 收藏 / 取消收藏 某篇新闻 (切换状态)"""
@router.post("/toggle/{news_id}", response_model=ApiResponse)
async def toggle_collect(
    news_id: int,                            # 从 URL 路径中获取新闻 ID
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # 告诉 CRUD 去切换状态，并返回操作结果（是"收藏成功"还是"取消成功"）
    is_collected = await toggle_collect_news(db, user.id, news_id)
    
    message = "收藏成功" if is_collected else "取消收藏成功"
    return ApiResponse(code=200, message=message)