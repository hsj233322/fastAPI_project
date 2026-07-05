# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from crud import users
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db
from schemas.users import UserRegisterRequest
from utils.security import verify_password
from schemas.users import LoginData, UserInfo, UserUpdateRequest, UserLoginRequest, ChangePasswordRequest
from schemas import ApiResponse
from models.users import User
from utils.auth import get_current_user

# 创建 APIRuter 实例
router = APIRouter(prefix='/api/user',tags=["个人中心"])

"""用户注册"""
@router.post("/register", response_model=ApiResponse)
async def register(user_data: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    # 查数据库，看用户名是否存在
    db_user = await users.get_user_by_username(db, user_data.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")
    # 创建用户并写入数据库
    await users.create_user(db, user_data)

    return ApiResponse(code=200, message="注册成功")
    
    
"""用户登录"""
@router.post("/login", response_model=ApiResponse[LoginData])
async def login(user_data: UserLoginRequest, db: AsyncSession = Depends(get_db)): 
    # 查用户
    db_user = await users.get_user_by_username(db, user_data.username)
    if not db_user or not verify_password(user_data.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    
    # 生成 Token
    token = await users.create_token(db, db_user.id)

    # 组装返回数据
    user_info = UserInfo.model_validate(db_user)
    login_data = LoginData(token=token, user_info=user_info)

    return ApiResponse(data=login_data)


"""获取个人中心"""
@router.get("/profile", response_model=ApiResponse[UserInfo])
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    user_info = UserInfo.model_validate(current_user)
    return ApiResponse(data=user_info)

"""修改个人资料"""
@router.patch("/profile", response_model=ApiResponse[UserInfo])
async def update_profile(
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_user = await users.update_user(db, current_user, user_data)

    return ApiResponse(data=UserInfo.model_validate(updated_user))

"""修改密码"""
@router.put("/password", response_model=ApiResponse)
async def update_password(
    user_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    await users.update_password(db, user, user_data)
    return ApiResponse(code=200, message="密码修改成功")