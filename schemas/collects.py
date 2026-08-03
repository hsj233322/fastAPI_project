# schemas/collects.py
from datetime import datetime
from schemas import BaseSchema
from typing import Annotated
from pydantic import Field

class CollectInternshipInfo(BaseSchema):
    """收藏列表里，单条岗位的响应模型"""
    internship_id : Annotated[int, Field(description="岗位 ID")]
    title : Annotated[str, Field(description="岗位标题")]
    category_name : Annotated[str, Field(description="所属分类名")]
    created_at : Annotated[datetime, Field(description="收藏时间")]