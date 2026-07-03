# models/users.py
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Index, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    用户信息表ORM模型
    """
    __tablename__ = "user"

    # 创建索引
    __table_args__ = (
        Index('phone_UNIQUE', 'phone'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    nickname: Mapped[str | None] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像URL", default="")
    gender: Mapped[str | None] = mapped_column(
        Enum("male", "female", "unknown"), comment="性别", default="unknown"
    )
    bio: Mapped[str | None] = mapped_column(String(500), comment="简介", default="这个人很懒，什么都没有留下")
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, nickname={self.nickname})>"
    
class UserToken(Base):
    """
    用户令牌表ORM模型
    """
    __tablename__ = "user_token"

    # 创建索引
    __table_args__ = (
        Index('token_UNIQUE', 'token'),
        Index('fk_user_token_user_idx', 'user_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="令牌ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="令牌过期时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    def __repr__(self) -> str:
        return f"<UserToken(id={self.id}, user_id={self.user_id}, token={self.token})>"