from pydantic import BaseModel, Field
from typing import Annotated

class UserRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]
