# schemas/collects.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# 收藏列表里，单条新闻的响应模型
class CollectNewsInfo(BaseSchema):
    id: int              # 新闻 ID
    title: str           # 新闻标题
    category_name: str   # 所属分类名
    created_at: datetime # 收藏时间