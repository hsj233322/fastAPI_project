# routers/historys.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from utils.auth import get_current_user
from models.users import User
from schemas import ApiResponse
from crud import historys
from schemas.historys import HistoryItemResponse
from models.news import News
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/history", tags=["浏览历史"])

""" 记录浏览历史 """
@router.post("/record/{news_id}", response_model=ApiResponse)
async def record_history(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    news = await db.get(News, news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新闻不存在")
    await historys.add_view_history(db, user.id, news_id)
    return ApiResponse(code=200, message="记录成功")

""" 获取我的浏览历史列表 """
@router.get("/list", response_model=ApiResponse[list[HistoryItemResponse]])
async def get_my_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    history_list = await historys.get_user_history(db, user.id)
    history_item = [HistoryItemResponse.model_validate(item) for item in history_list]
    return ApiResponse(data=history_item)

""" 删除单条浏览历史 """
@router.delete("/{record_id}", response_model=ApiResponse)
async def delete_one_history(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    await historys.delete_one_history(db, record_id, user.id)
    return ApiResponse(code=200, message="删除成功")

""" 删除我的浏览历史列表 """
@router.delete("/", response_model=ApiResponse)
async def delete_all_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    await historys.delete_all_history(db, user.id)
    return ApiResponse(code=200, message="删除成功")