# models/users.py
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Index, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, TimestampMixin
from sqlalchemy.dialects.mysql import INTEGER

class User(Base, TimestampMixin):
    """
    用户信息表ORM模型
    """
    __tablename__ : str = "user"

    # 创建索引
    __table_args__ : tuple[Index, ...] = (  
        Index('phone_UNIQUE', 'phone'),
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    nickname: Mapped[str | None] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像URL", default="")
    gender: Mapped[str | None] = mapped_column(
        Enum("male", "female", "unknown"), comment="性别", default="unknown"
    )
    bio: Mapped[str | None] = mapped_column(String(500), comment="简介", default="这个人很懒，什么都没有留下")
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")
    
class UserToken(Base):
    """
    用户令牌表ORM模型
    """
    __tablename__ : str = "user_token"

    # 创建索引
    __table_args__ : tuple[Index, ...] = (
        Index('token_UNIQUE', 'token'),
        Index('fk_user_token_user_idx', 'user_id'),
    )

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=True, comment="令牌ID")
    user_id: Mapped[int] = mapped_column(INTEGER(unsigned=True), ForeignKey('user.id'), nullable=False, comment="用户ID")
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="令牌过期时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )