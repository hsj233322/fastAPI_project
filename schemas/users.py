# schemas/users.py
from pydantic import BaseModel, Field, field_validator
from typing import Annotated
from schemas import BaseSchema
import re

# ================= 请求模型 =================

class UserRegisterRequest(BaseModel):
    """注册接口的请求模型"""
    username: Annotated[str, Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",   # 只允许字母、数字、下划线
        description="用户名，3-50位，仅支持字母、数字和下划线"
    )]
    password: Annotated[str, Field(
        min_length=8,
        max_length=128,
        description="密码，8-128位，需包含大写字母、小写字母和数字"
    )]

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含小写字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含数字")
        return v

class UserLoginRequest(BaseModel):
    """登录接口的请求模型"""
    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=8, max_length=128, description="密码")]

class ChangePasswordRequest(BaseModel):
    """修改密码接口的请求模型"""
    old_password: Annotated[str, Field(min_length=8, max_length=128, description="旧密码")]
    new_password: Annotated[str, Field(min_length=8, max_length=128, description="新密码，8-128位，需包含大写字母、小写字母和数字")]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含小写字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含数字")
        return v

class UserUpdateRequest(BaseModel):
    """更新个人资料的请求模型，可更新部分数据"""
    bio: str | None = None
    avatar: str | None = None

# ================= 响应模型 =================

class UserInfo(BaseSchema):
    """用户基础信息"""
    id: int
    username: str
    bio: str | None = None
    avatar: str | None = None

class LoginData(BaseSchema):
    """登录成功返回的 data 数据"""
    token: str
    user_info: UserInfo