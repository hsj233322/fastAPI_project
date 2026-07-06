# schemas/historys.py
from schemas import BaseSchema
from datetime import datetime

class HistoryItemResponse(BaseSchema):
    """浏览历史中每一项的响应模型"""
    id: int
    title: str
    image: str | None = None 
    category_name: str
    view_time: datetime