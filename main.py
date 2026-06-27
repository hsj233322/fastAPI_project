from fastapi import FastAPI, Request
from routers import news, users
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.requests import Request
from fastapi.responses import JSONResponse
from loguru import logger

app = FastAPI()

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



"""--------异常处理--------"""
# 配置 loguru 自动生成日志文件
# rotation="00:00" 表示每天午夜自动生成一个新文件
# retention="10 days" 表示只保留最近 10 天的日志，自动删除老日志
# enqueue=True 表示异步写入，高并发下不会阻塞接口响应


# 全局 HTTP 异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request:Request, exc:HTTPException):
    """
    只要代码里 raise HTTPException，就会被这个函数拦截
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
   "logs/error.log", level="ERROR",
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