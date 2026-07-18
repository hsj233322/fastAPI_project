# schemas/historys.py
from schemas import BaseSchema
from datetime import datetime

class HistoryItemResponse(BaseSchema):
    id: int                # 浏览记录 ID
    internship_id: int     # 岗位 ID
    title: str             # 岗位名称
    company_name: str      # 公司名称
    view_time: datetime    # 浏览时间