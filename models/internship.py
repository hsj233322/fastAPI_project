# models/Internship.py
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Index, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, TimestampMixin


class InternshipCategory(Base, TimestampMixin):
    """实习岗位分类"""
    __tablename__: str = "internship_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    category_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")


class Internship(Base, TimestampMixin):
    """实习岗位主表"""
    __tablename__: str = "internship"

    __table_args__: tuple[Index, ...] = (
        Index('idx_category_id', 'category_id'),
        Index('idx_publish_time', 'publish_time'),
        Index('uk_position_id', 'position_id', unique=True),  # 爬虫去重唯一索引
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="岗位自增ID")
    position_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False, comment="原始职位ID（去重）")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="岗位名称")
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="单位名称")
    province: Mapped[str] = mapped_column(String(50), nullable=False, comment="省份")
    salary_min: Mapped[int] = mapped_column(Integer, comment="最低月薪（单位：k）")
    salary_max: Mapped[int] = mapped_column(Integer, comment="最高月薪（单位：k）")
    headcount: Mapped[int] = mapped_column(Integer, default=0, comment="招聘人数")
    education: Mapped[str | None] = mapped_column(String(50), comment="学历要求")
    major: Mapped[str | None] = mapped_column(Text, comment="专业要求（逗号分隔）")
    company_type: Mapped[str | None] = mapped_column(String(100), comment="单位性质")
    company_scale: Mapped[str | None] = mapped_column(String(50), comment="单位规模")
    tags: Mapped[str | None] = mapped_column(String(500), comment="福利标签（逗号分隔）")
    description: Mapped[str | None] = mapped_column(Text, comment="岗位描述或职责（可选）")
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="发布时间"
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("internship_category.id"), comment="分类ID"
    )