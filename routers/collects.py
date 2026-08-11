# routers/collects.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import Annotated

from config.db_config import get_db
from utils.auth import get_current_user
from models.users import User
from schemas import ApiResponse
from schemas.collects import CollectInternshipInfo
from crud import collects as crud_collects

router = APIRouter(prefix="/api/collects", tags=["岗位收藏"])


@router.get("/list", response_model=ApiResponse[list[CollectInternshipInfo]])
async def get_my_collects(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    collects_list = await crud_collects.get_user_collects(db, user.id)
    # 注意：get_user_collects 返回的是元组/行，需要转为 Pydantic 模型
    items = [CollectInternshipInfo.model_validate(c) for c in collects_list]
    return ApiResponse(data=items)


@router.post("/toggle/{internship_id}", response_model=ApiResponse[None])
async def toggle_collect(
    internship_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[None]:
    # 查询是否已收藏
    from sqlalchemy import select
    from models.collects import Collect

    exists = await db.execute(
        select(Collect).where(
            Collect.user_id == user.id,
            Collect.internship_id == internship_id,
        )
    )
    record = exists.scalar_one_or_none()

    if record:
        # 已收藏 → 取消
        await db.delete(record)
        await db.commit()
        return ApiResponse(code=200, message="取消收藏成功")
    else:
        # 未收藏 → 添加（带并发保护的复合唯一约束）
        try:
            db.add(Collect(user_id=user.id, internship_id=internship_id))
            await db.commit()
        except IntegrityError:
            # 并发场景下的重复收藏，直接返回成功
            # （复合唯一约束已生效，不会产生重复数据）
            await db.rollback()
            return ApiResponse(code=200, message="收藏成功")
        return ApiResponse(code=200, message="收藏成功")


@router.delete("/delete", response_model=ApiResponse[None])
async def de_collect_all(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[None]:
    await crud_collects.clear_user_collects(db, user.id)
    return ApiResponse(code=200, message="清空收藏成功")