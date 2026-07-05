from pydantic import BaseModel
from typing import Generic, TypeVar
from pydantic.config import ConfigDict

T = TypeVar("T")

# ==================== 通用响应模型 ====================
class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)