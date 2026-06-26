from fastapi import APIRouter, Depends, Query, HTTPException
from crud import news, users
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from typing import Annotated
from schemas.users import UserRequest
from starlette import status
from schemas.response import LoginResponse

# 创建 APIRuter 实例
router = APIRouter(prefix='/api/user',tags=["users"])

@router.post("/register", response_model=LoginResponse)
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)):

    # 用户注册逻辑：验证用户是否存在 → 创建用户 → 生成Token → 相应结果
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")
    user = await users.create_user(db, user_data)

    token = await users.create_token(db, user.id)

    return{
        "code": 200,
        "message": "注册成功",
        "data":{
            "token": token,
            "userInfo":{
                "id": user.id,
                "username": user.username,
                "bio": user.bio,
                "avatar": user.avatar
            }
        }
    }