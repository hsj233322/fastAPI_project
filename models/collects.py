# models/collects.py
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, TimestampMixin
from models.users import User
from models.internship import Internship
from sqlalchemy import Integer



class Collect(Base, TimestampMixin):
    __tablename__ : str = "internship_collect"

    # 复合唯一约束：防止同一用户重复收藏同一岗位
    __table_args__ = (
        UniqueConstraint('user_id', 'internship_id', name='uq_user_internship'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏记录ID")
    user_id: Mapped[int] = mapped_column(
         Integer, ForeignKey(User.id, ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    internship_id: Mapped[int] = mapped_column(
         Integer, ForeignKey(Internship.id, ondelete="CASCADE"), nullable=False, comment="实习岗位ID"
    )