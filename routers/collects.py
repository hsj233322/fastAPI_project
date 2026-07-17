# routers/collects.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from utils.auth import get_current_user
from models.users import User
from schemas import ApiResponse
from schemas.collects import CollectNewsInfo
from crud.collects import get_user_collects, toggle_collect_news
from crud.collects import de_collect_all
from typing import Annotated

router = APIRouter(prefix="/api/collects", tags=["新闻收藏"])

""" 获取我的收藏列表 """
@router.get("/list", response_model=ApiResponse[list[CollectNewsInfo]])
async def get_my_collects(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)]
):
    collects_list = await get_user_collects(db, user.id)
    return ApiResponse(data=collects_list)

""" 收藏 / 取消收藏 某篇新闻 (切换状态) """
@router.post("/toggle/{news_id}", response_model=ApiResponse[None])
async def toggle_collect(
    news_id: int, 
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)]
)-> ApiResponse[None]:
    is_collected = await toggle_collect_news(db, user.id, news_id)
    
    message = "收藏成功" if is_collected else "取消收藏成功"
    return ApiResponse(code=200, message=message)

""" 清空收藏 """
@router.delete("/delete", response_model=ApiResponse[None])
async def de_collect_list(
    db: Annotated[AsyncSession, Depends(get_db)],
    user : Annotated[User, Depends(get_current_user)]
)-> ApiResponse[None]:
    await de_collect_all(db, user.id)
    return ApiResponse(code=200, message="清空收藏成功")