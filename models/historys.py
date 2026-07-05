# models/historys.py
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from models import Base
from sqlalchemy.dialects.mysql import INTEGER
from models.users import User
from models.news import News

class ViewHistory(Base):
    __tablename__ = "news_view_history"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="记录ID")
    
    user_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey(User.id, ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    
    news_id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), ForeignKey(News.id, ondelete="CASCADE"), nullable=False, comment="新闻ID"
    )


    view_time: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),     # 第一次插入时，记录当前时间
        onupdate=lambda: datetime.now(timezone.utc),    # 如果这条记录被修改了，自动把时间更新为当前时间
        comment="最后浏览时间"
    )