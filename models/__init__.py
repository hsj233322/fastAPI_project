# models/__init__.py
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的统一基类，仅负责元数据注册。"""
    pass


class TimestampMixin:
    """
    时间戳混入类。
    需要 created_at / updated_at 的模型，继承时加上这个 Mixin。
    不需要时间戳的模型，不加即可。
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新时间",
    )