# schemas/news.py
from pydantic import BaseModel
from typing import Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

# 通用的 API 响应模型
class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None

# 分类标签
class CategoryRequest(BaseModel):
    id: int
    name: str
    sort_order: int

    model_config = {"from_attributes": True}

# 列表页每条新闻展示的内容
class NewsListItemRequest(BaseModel):
    id: int
    title: str
    image: str
    author: str
    publish_time: datetime
    category_id: int
    views: int
    model_config = {"from_attributes": True}

# 分页模型
class PaginatedNews(BaseModel):
    list: list[NewsListItemRequest]
    total: int
    has_more: bool
    
    model_config = {"from_attributes": True}

# 详情页下的相关新闻
class RelatedNews(BaseModel):
    id: int
    title: str
    publish_time: datetime
    views: int

    model_config = {"from_attributes": True}

# 新闻详情
class NewsDetail(BaseModel):
    id: int
    title: str
    content: str
    image: str
    author: str
    publish_time: datetime
    category_id: int
    views: int
    related_news: list[RelatedNews] = []

    model_config = {"from_attributes": True}
