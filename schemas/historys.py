# schemas/historys.py
from schemas import BaseSchema
from datetime import datetime

class HistoryItemResponse(BaseSchema):
    """浏览历史"""
    id: int
    title: str
    image: str | None = None 
    category_name: str
    view_time: datetime