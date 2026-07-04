# models/collects.py
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, TimestampMixin
from models.users import User
from models.news import News
from sqlalchemy.dialects.mysql import INTEGER

class Collect(Base, TimestampMixin):
    __tablename__ = "news_collect"

    
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="收藏记录ID")
    user_id: Mapped[int] = mapped_column(
         INTEGER(unsigned=True), ForeignKey(User.id, ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    news_id: Mapped[int] = mapped_column(
         INTEGER(unsigned=True), ForeignKey(News.id, ondelete="CASCADE"), nullable=False, comment="新闻ID"
    )

    def __repr__(self) -> str:
        return f"<Collect(id={self.id}, user_id={self.user_id}, news_id={self.news_id})>"