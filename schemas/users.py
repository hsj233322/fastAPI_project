# schemas/users.py
from pydantic import BaseModel, Field, ConfigDict 
from typing import Annotated
from schemas import BaseSchema

# ================= 请求模型 =================

class UserRegisterRequest(BaseModel):
    """注册接口的请求模型"""
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]

class UserLoginRequest(BaseModel):
    """登录接口的请求模型"""
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]

class ChangePasswordRequest(BaseModel):
    """修改密码接口的请求模型"""
    old_password: Annotated[str, Field(min_length=6, max_length=128, description="旧密码")]
    new_password: Annotated[str, Field(min_length=6, max_length=128, description="新密码")]

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