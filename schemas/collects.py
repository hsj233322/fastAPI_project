# schemas/collects.py
from datetime import datetime
from schemas import BaseSchema

class CollectInternshipInfo(BaseSchema):
    """收藏列表里，单条岗位的响应模型"""
    internship_id: int   # 岗位 ID
    title: str           # 岗位标题
    category_name: str   # 所属分类名
    created_at: datetime # 收藏时间