from fastapi import APIRouter

# 创建 APIRuter 实例
router = APIRouter(prefix='/api/news',tags=["news"])
# prefix 是公共的url前缀，会自动补全下面所有的路由方法中的url，不需要再重复写

@router.get("/categories")  # 这里的url相当于/api/news/categories
async def get_categories(skip: int=0, limit: int=100):
    return {
        "code": 200,
        "message": "success",
        "data": "新闻分类列表"
    }