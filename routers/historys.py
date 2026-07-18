# routers/historys.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from config.db_config import get_db
from utils.auth import get_current_user
from models.users import User
from schemas import ApiResponse
from crud import historys
from schemas.historys import HistoryItemResponse
from models.internship import Internship
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/history", tags=["浏览历史"])


@router.post("/record/{internship_id}", response_model=ApiResponse[None])
async def record_history(
    internship_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[None]:
    internship = await db.get(Internship, internship_id)
    if not internship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    await historys.add_view_history(db, user.id, internship_id)
    return ApiResponse(code=200, message="记录成功")


@router.get("/list", response_model=ApiResponse[list[HistoryItemResponse]])
async def get_my_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    history_list = await historys.get_user_history(db, user.id)
    history_items = [
        HistoryItemResponse.model_validate(item) for item in history_list
    ]
    return ApiResponse(data=history_items)


@router.delete("/{record_id}", response_model=ApiResponse[None])
async def delete_one_history(
    record_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[None]:
    await historys.delete_one_history(db, record_id, user.id)
    return ApiResponse(code=200, message="删除成功")


@router.delete("/", response_model=ApiResponse[None])
async def delete_all_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[None]:
    await historys.delete_all_history(db, user.id)
    return ApiResponse(code=200, message="清空成功")