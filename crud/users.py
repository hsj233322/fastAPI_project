# crud/users.py
import secrets

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserToken
from schemas.users import UserRegisterRequest, UserInfo, UserUpdateRequest, ChangePasswordRequest
from utils import security
from fastapi import HTTPException, status
from utils.security import verify_password, get_hash_password

async def get_user_by_username(db: AsyncSession, username: str):
    """根据用户名查询用户"""
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_data: UserRegisterRequest):
    """创建新用户"""
    hashed_password = security.get_hash_password(user_data.password)

    user = User(
        username=user_data.username,
        password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_token(db: AsyncSession, user_id: int):
    """生成或更新用户 Token"""
    token = secrets.token_urlsafe(32) 
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    query = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(query)
    user_token = result.scalar_one_or_none()

    if user_token:
        user_token.token = token
        user_token.expires_at = expires_at
    else:
        user_token = UserToken(
            token=token,
            expires_at=expires_at,
            user_id=user_id,
        )
        db.add(user_token)

    await db.commit() 
    await db.refresh(user_token)
    return token


async def update_user(
        db: AsyncSession,
        user: User, # 工具函数 auth 查出来的 ORM 对象
        update_data: UserUpdateRequest,   # 前端传来的部分数据
):
    """更新用户信息"""
    update_dict = update_data.model_dump(exclude_unset=True)    # 只获取前端实际传过来的字段，转成字典

    # 遍历字典，动态覆盖 ORM 对象的属性
    for key, value in update_dict.items():
        setattr(user, key, value)   # 等同于 user.key = value   user.bio = "新简介"

    await db.commit()       # 提交更改到数据库
    await db.refresh(user)  # 刷新对象，确保数据是最新的
    return user

async def update_password(
        db: AsyncSession,
        user: User,
        update_data: ChangePasswordRequest,
):
    """更新用户密码"""
    
    # 验证旧密码是否正确
    if not verify_password(update_data.old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 加密新密码
    new_hashed_password = get_hash_password(update_data.new_password)

    # 更新用户密码
    user.password = new_hashed_password

    # 提交并刷新
    await db.commit()
    await db.refresh(user)
    return user