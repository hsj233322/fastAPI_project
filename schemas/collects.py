# schemas/collects.py
from datetime import datetime
from schemas import BaseSchema

class CollectNewsInfo(BaseSchema):
    """收藏列表里，单条新闻的响应模型"""
    news_id: int              # 新闻 ID
    title: str           # 新闻标题
    category_name: str   # 所属分类名
    created_at: datetime # 收藏时间