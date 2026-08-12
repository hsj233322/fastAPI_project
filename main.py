from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import os

from config.redis_config import redis_pool
from dependencies import start_background_tasks, stop_background_tasks 

# 路由
from routers import internship, users, collects, historys, ai_assistant

# 数据库相关
from models import Base 
from config.db_config import async_engine

"""注册模型，触发建表"""
from models.collects import Collect     
from models.historys import ViewHistory
from models.internship import Internship, InternshipCategory

import logging

# 统一设置全局日志级别为 INFO，确保所有模块的 logger.info 都能正常输出
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    # 1. 初始化数据库表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. 启动后台任务
    # 3. 传入数据库会话工厂（用来创建新的数据库会话）
    await start_background_tasks(async_session_factory)
    
    print("Application startup complete")
    
    yield  # 应用运行期间
    
    # --- 关闭阶段 ---
    # 先停业务任务（触发最后一次刷库），再关底层连接池
    await stop_background_tasks()       # 1. 停止刷库任务并刷入剩余数据
    await redis_pool.aclose()           # 2. 关闭 Redis 连接池
    await async_engine.dispose()        # 3. 释放数据库引擎
    print("All resources released")


# 4. 在创建 app 之前定义 session_factory
async_session_factory = async_sessionmaker(
    async_engine, 
    expire_on_commit=False  # 禁用自动过期，确保会话在请求完成后手动关闭
    # 这样可以避免数据库连接池中的连接被重复使用，提高性能
)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(internship.router)
app.include_router(users.router)
app.include_router(collects.router)
app.include_router(historys.router)
app.include_router(ai_assistant.router)

# 挂载前端静态资源（放在路由之后，避免拦截 /api 请求）
# 通过访问 http://localhost:8000/ 即可打开前端页面
_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

"""--------异常处理--------"""
logger.add(
   "logs/server_error_{time:YYYY-MM-DD}.log",
   rotation="00:00",
   retention="10 days",
   enqueue=True
)

# 全局 HTTP 异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,    
            "data": None               
        }
    )

# 数据库完整性约束异常处理器
@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    logger.error(f"数据库完整性约束错误: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": "数据完整性约束错误（可能是重复提交或关联数据不存在）",
            "data": None
        }
    )

# 数据库操作异常处理器
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"数据库操作错误: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "数据库操作失败",
            "data": None
        }
    )

# 全局未知异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"服务器内部崩溃: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None
        }
    )