# routers/users.py

from pydantic import BaseModel, Field
from typing import Annotated
from pydantic.config import ConfigDict

class UserRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]

# 定义用户基础信息
class UserInfo(BaseModel):
    id: int
    username: str
    bio: str | None = None
    avatar: str | None = None
    model_config = ConfigDict(from_attributes=True)

# 定义登录成功后，data 里面要装的具体结构
class LoginData(BaseModel):
    token: str
    userInfo: UserInfo  # 这里直接引用上面的模型