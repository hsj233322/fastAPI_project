from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.users import User
from schemas.users import UserRequest
from utils import security

# 判断用户是否已注册
async def get_user_by_username(db: AsyncSession, username: str):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()

# 创建用户
async def create_user(db: AsyncSession, user_data: UserRequest):
    # 密码加密
    hashed_password = security.get_hash_password(user_data.password)
    
    user = User(
        username=user_data.username, 
        password=hashed_password
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)  # 从数据库读回最新的user
    return user