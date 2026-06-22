from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy import Integer, String

# 定义基础模型类
class Base(DeclarativeBase):
    '''
    所有数据库表的基表。
    其他表（如新闻分类表，用户表）都会继承这个类，从而自动拥有创建时间和更新时间字段。
    '''

    # 创建时间字段 
    create_at : Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间"
    )

    # 更新时间字段
    updated_at : Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,  # 每次更新数据时，自动把时间刷新为当前时间
        comment="更新时间"
    )

class Category(Base):
    __tablename__ = "news_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment='分类名称')
    sort_order: mapped_column[int] = mapped_column(Integer, default=0, nullable=False, comment='排序')

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name}, sort_order={self.sort_order})>"