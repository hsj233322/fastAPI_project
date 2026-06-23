from fastapi import APIRouter, Depends
from crud import news
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_db

# 创建 APIRuter 实例
router = APIRouter(prefix='/api/news',tags=["news"])
# prefix 是公共的url前缀，会自动补全下面所有的路由方法中的url，不需要再重复写

@router.get("/categories")  # 这里的url相当于/api/news/categories
async def get_categories(skip: int=0, limit: int=100, db: AsyncSession = Depends(get_db)):

    categories = await news.get_categories(db, skip, limit)

    return {
        "code": 200,
        "message": "success",
        "data": categories
    }