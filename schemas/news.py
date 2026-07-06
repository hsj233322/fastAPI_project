# schemas/news.py
from pydantic import BaseModel
from datetime import datetime
from schemas import BaseSchema

# ==================== 新闻分类 ====================
class CategoryResponse(BaseSchema):
    """分类响应模型"""
    id: int
    category_name: str
    sort_order: int

# ==================== 新闻列表 ====================
class NewsListItemResponse(BaseSchema):
    """新闻列表中的每一项响应模型"""
    id: int
    title: str
    image: str
    author: str
    publish_time: datetime
    category_id: int
    views: int

class PaginatedNewsResponse(BaseSchema):
    """分页响应"""
    item: list[NewsListItemResponse]
    total: int
    has_more: bool

# ==================== 新闻详情 ====================
class RelatedNewsResponse(BaseSchema):
    """相关新闻"""
    id: int
    title: str
    publish_time: datetime
    views: int

class NewsDetailResponse(BaseSchema):
    """新闻详情响应模型"""
    id: int
    title: str
    content: str
    image: str
    author: str
    publish_time: datetime
    category_id: int
    views: int
    related_news: list[RelatedNewsResponse] = []    # 相关新闻