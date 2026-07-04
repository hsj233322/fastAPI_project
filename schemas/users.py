# schemas/users.py
from pydantic import BaseModel, Field, ConfigDict 
from typing import Annotated

# ================= 基础配置 ================= 

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# ================= 请求模型 =================

# 注册接口的请求模型
class UserRegisterRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]

# 登陆接口请求模型
class UserLoginRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]

# 修改密码请求模型
class ChangePasswordRequest(BaseModel):
    old_password: Annotated[str, Field(min_length=6, max_length=128, description="旧密码")]
    new_password: Annotated[str, Field(min_length=6, max_length=128, description="新密码")]

# 更新部分数据请求模型
class UserUpdateRequest(BaseModel):
    bio: str | None = None
    avatar: str | None = None

# ================= 响应模型 =================

# 用户基础信息
class UserInfo(BaseSchema):
    id: int
    username: str
    bio: str | None = None
    avatar: str | None = None

# 登录成功后，data 里面要装的具体结构
class LoginData(BaseSchema):
    token: str
    user_info: UserInfo

# 登陆接口的返回值类型就是： ApiResponse[LoginData]