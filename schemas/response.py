# schemas/response.py
from pydantic import BaseModel
from schemas.users import LoginData

# 登录接口的响应模型
class LoginResponse(BaseModel):
    code: int = 200
    message: str = "登录成功"
    data: LoginData | None = None 