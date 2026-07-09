from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from config.redis_config import redis_pool

# 路由
from routers import news, users, collects, historys

# 数据库相关
from models import Base 
from config.db_config import async_engine, get_db 
"""注册模型，触发建表"""
from models.collects import Collect     
from models.historys import ViewHistory


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    # 1. 初始化数据库表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. 检查 Redis（from_url 是懒加载的，已经准备好了，所以这里无需操作）
    print("Redis 连接池已就绪")
    
    yield  # 应用运行期间
    
    # --- 关闭阶段 ---
    # 注意：关闭顺序通常和启动相反
    await redis_pool.aclose()
    await async_engine.dispose()
    print("所有连接池已释放")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"], # 允许前端的地址
    allow_credentials=True,
    allow_methods=["*"], # 允许所有请求方法 (GET, POST 等)
    allow_headers=["*"], # 允许所有请求头
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

# 挂载路由
app.include_router(news.router)
app.include_router(users.router)
app.include_router(collects.router)
app.include_router(historys.router)



"""--------异常处理--------"""
# 配置 loguru 自动生成日志文件
# rotation="00:00" 表示每天午夜自动生成一个新文件
# retention="10 days" 表示只保留最近 10 天的日志，自动删除老日志
# enqueue=True 表示异步写入，高并发下不会阻塞接口响应

# 全局 HTTP 异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request:Request, exc:HTTPException):
    """
    只要代码里 raise HTTPException就会被这个函数拦截
    """
    # 把 FastAPI 默认的 detail, 转换成项目统一的 message
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,    # 使用 HTTP 状态码作为业务 code
            "message": exc.detail,      # 使用 HTTP 状态码的 detail 作为 message    
            "data": None                # 发生错误时，data 默认为 None
        }
    )

logger.add(
   "logs/server_error_{time:YYYY-MM-DD}.log",
    enqueue=True
)
# 全局未知异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request:Request, exc:Exception):
    """
    只要代码发生了没被捕获的崩溃就会被这里拦截
    """
    # logger.exception 会自动把详细的报错堆栈全部写进日志文件
    logger.exception(f"服务器内部崩溃: {exc}")

    # 给前端返回一个统一的错误提示
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None
        }
    )