# crud/users.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.users import UserRegisterRequest, UserUpdateRequest, ChangePasswordRequest
from utils import security
from fastapi import HTTPException, status
from utils.security import verify_password, get_hash_password

async def get_user_by_username(db: AsyncSession, username: str):
    """根据用户名查询用户"""
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int):
    """根据用户ID查询用户"""
    query = select(User).where(User.id == user_id)
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


async def update_user(
        db: AsyncSession,
        user_id: int,
        update_data: UserUpdateRequest,   # 前端传来的部分数据
):
    """更新用户信息"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 遍历字典，动态覆盖 ORM 对象的属性
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)   # 等同于 user.key = value   user.bio = "新简介"

    await db.commit()       # 提交更改到数据库
    await db.refresh(user)  # 刷新对象，确保数据是最新的
    return user

async def update_password(
        db: AsyncSession,
        user_id: int,
        update_data: ChangePasswordRequest,
):
    """更新用户密码"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if update_data.new_password == update_data.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

    # 验证旧密码是否正确
    if not verify_password(update_data.old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 加密新密码
    new_hashed_password = get_hash_password(update_data.new_password)

    # 更新用户密码和 token_version
    user.password = new_hashed_password
    user.token_version += 1

    # 提交并刷新
    await db.commit()
    await db.refresh(user)
    return user