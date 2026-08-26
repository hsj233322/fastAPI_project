# models/historys.py
from sqlalchemy import ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from models import Base
from sqlalchemy import Integer
from models.users import User
from models.internship import Internship

class ViewHistory(Base):
    __tablename__ : str = "internship_view_history"

    # 复合索引：覆盖按 (user_id, internship_id) 查找更新；最左前缀覆盖按 user_id 的列表/清空查询
    __table_args__ = (
        Index('idx_user_internship', 'user_id', 'internship_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(User.id, ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    
    internship_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(Internship.id, ondelete="CASCADE"), nullable=False, comment="实习岗位ID"
    )


    view_time: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="最后浏览时间(UTC)"
    )