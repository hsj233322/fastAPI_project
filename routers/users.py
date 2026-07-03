# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from crud import users
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from schemas.users import UserRequest
from utils.security import verify_password
from schemas.users import LoginResponse, LoginData, UserInfo

# 创建 APIRuter 实例
router = APIRouter(prefix='/api/user',tags=["users"])

"""用户注册"""
@router.post("/register", response_model=LoginResponse)
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    # 用户注册逻辑：验证用户是否存在 → 创建用户 → 生成Token → 相应结果
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")
    
    # 创建用户
    user = await users.create_user(db, user_data)
    # 生成Token
    token = await users.create_token(db, user.id)

    return LoginResponse(
        code=200,             # 你的模型里定义了 code=200，这里可以省略，但写上更明确
        message="注册成功",   # 关键字参数写法：key=value
        data=LoginData(
            token=token,
            userInfo=UserInfo.model_validate(user)
        )
    )

"""用户登录"""
@router.post("/login", response_model=LoginResponse)
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)): 
    user = await users.get_user_by_username(db, user_data.username)
    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    
    token = await users.create_token(db, user.id)

    return {
        "data": {
            "token": token,
            "userInfo": user
        }
    }