# schemas/internship.py
from datetime import datetime
from schemas import BaseSchema


# ==================== 岗位分类 ====================
class CategoryResponse(BaseSchema):
    """分类响应模型"""
    id: int
    category_name: str
    sort_order: int


# ==================== 岗位列表 ====================
class InternshipListItemResponse(BaseSchema):
    """岗位列表中的每一项"""
    id: int
    position_id: str
    title: str
    company_name: str
    province: str
    salary_min: int
    salary_max: int
    headcount: int
    education: str | None = None
    tags: str | None = None
    publish_time: datetime
    views: int


class PaginatedInternshipResponse(BaseSchema):
    """分页响应（注意：items 修正了原 item 的拼写）"""
    items: list[InternshipListItemResponse]
    total: int
    has_more: bool


# ==================== 岗位详情 ====================
class RelatedInternshipResponse(BaseSchema):
    """相关岗位推荐"""
    id: int
    title: str
    company_name: str
    publish_time: datetime
    views: int


class InternshipDetailResponse(BaseSchema):
    """岗位详情响应"""
    id: int
    position_id: str
    title: str
    company_name: str
    province: str
    salary_min: int
    salary_max: int
    headcount: int
    education: str | None = None
    major: str | None = None
    company_type: str | None = None
    company_scale: str | None = None
    tags: str | None = None
    description: str | None = None
    views: int
    publish_time: datetime
    category_id: int | None = None
    related_internships: list[RelatedInternshipResponse] = []