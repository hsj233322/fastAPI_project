# models/news.py
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Index, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models import Base, TimestampMixin

class Category(Base, TimestampMixin):
    __tablename__ = "news_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    category_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")

    
class News(Base, TimestampMixin):
    __tablename__ = "news"

    # 创建索引
    __table_args__ = (
        Index('fk_news_category_idx', 'category_id'),
        Index('idx_publish_time', 'publish_time')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[str | None] = mapped_column(String(500), comment="新闻描述")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[str | None] = mapped_column(String(255), comment="封面图片URL")
    author: Mapped[str | None] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_category.id"), nullable=False, comment="分类ID"
    )
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="发布时间"
    )
