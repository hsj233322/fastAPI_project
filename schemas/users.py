# schemas/users.py
from pydantic import BaseModel, Field, ConfigDict 
from typing import Annotated

class UserRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# 定义用户基础信息
class UserInfo(BaseSchema):
    id: int
    username: str
    bio: str | None = None
    avatar: str | None = None

# 定义登录成功后，data 里面要装的具体结构
class LoginData(BaseSchema):
    token: str
    userInfo: UserInfo 

class LoginResponse(BaseSchema):
    code: int = 200
    message: str = "登录成功"
    data: LoginData | None = None