# config/db_config.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

# 1. 数据库 URL(优先读取环境变量，如果没有则使用默认的本地 localhost)
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL", 
    "mysql+aiomysql://myuser:123456@localhost:3306/news_app?charset=utf8mb4"
)

# 2. 创建异步引擎 (Engine)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,          
    pool_size=10,       
    max_overflow=20     
)

# 3. 创建异步会话工厂 (SessionLocal)
# 相当于生产 session（会话）的流水线
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False  # 提交后不让数据过期，防止后续读取数据时报错
)

# 4. 依赖项：用于获取数据库会话
# 这个函数会被 FastAPI 的 Depends() 调用，实现自动管理数据库连接的打开和关闭
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            # 把 session 传递给具体的路由函数去使用
            yield session
            # 路由函数执行完毕后，如果没有报错，就自动提交事务
            await session.commit()
        except Exception:
            # 如果路由函数执行过程中发生任何异常，就回滚（撤销）刚才的所有操作，保护数据库
            await session.rollback()
            raise  # 把异常继续抛出去，让 FastAPI 返回 500 错误
        # 【注意】：这里不需要写 finally: await session.close()
        # 因为使用了 async with 语法，Python 会在代码块结束时，自动且安全地关闭 session