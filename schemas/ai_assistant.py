# schemas/ai_assistant.py
from pydantic import BaseModel, Field
from schemas import BaseSchema
from typing import Annotated, Literal

class ChatMessage(BaseModel):
    """
    聊天消息模型。

    Attributes:
        role (str): 消息角色，例如 "user"、"assistant" 等。
        content (str): 消息内容。
    """
    role: Literal["user", "assistant"]  # 限制枚举，避免前端传 system 造成提示注入
    content : Annotated[str, Field(description="消息内容")]

class ChatRequest(BaseModel):
    """
    与 AI 助手对话的请求体。

    Attributes:
        message (str): 用户本次输入的提问内容，不可为空。
        session_id (str | None): 会话ID。
    """
    message : Annotated[str, Field(description="用户提问内容,不能为空")]
    session_id: Annotated[str | None, Field(description="会话ID，用于多轮对话")] = None

class RelatedJob(BaseSchema):
    """
    相关岗位推荐模型。

    Attributes:
        id (int): 岗位ID，用于唯一标识岗位。
        title (str): 岗位名称，描述岗位的具体工作内容。
    """
    id : Annotated[int, Field(description="岗位ID")]
    title : Annotated[str, Field(description="岗位名称")]
    company_name : Annotated[str, Field(description="公司名称")]
    salary_min: Annotated[int | None, Field(description="最低薪资(k)")] = None
    salary_max: Annotated[int | None, Field(description="最高薪资(k)")] = None
    province : Annotated[str, Field(description="省份")]
    education: Annotated[str | None, Field(description="学历要求")] = None
