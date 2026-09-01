# models/users.py
from sqlalchemy import String, Index, Enum
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from models import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    用户信息表ORM模型
    """
    __tablename__ : str = "user"

    # 创建索引
    __table_args__ : tuple[Index, ...] = (
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
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="JWT令牌版本号，修改密码或强制登出时+1"
    )