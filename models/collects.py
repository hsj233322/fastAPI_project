# models/collects.py
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, TimestampMixin
from models.users import User
from models.internship import Internship
from sqlalchemy import Integer



class Collect(Base, TimestampMixin):
    __tablename__ : str = "internship_collect"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏记录ID")
    user_id: Mapped[int] = mapped_column(
         Integer, ForeignKey(User.id, ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    internship_id: Mapped[int] = mapped_column(
         Integer, ForeignKey(Internship.id, ondelete="CASCADE"), nullable=False, comment="实习岗位ID"
    )