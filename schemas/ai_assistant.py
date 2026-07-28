from pydantic import BaseModel, Field
from schemas import BaseSchema
from typing import Annotated

class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：user 或 assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户提问内容")
    conversation_history: Annotated[list[ChatMessage] | None, Field(description="历史对话记录")] = None


class RelatedJob(BaseSchema):
    id: int = Field(..., description="岗位ID")
    title: str = Field(..., description="岗位名称")
    company_name: str = Field(..., description="公司名称")
    salary_min: Annotated[int | None, Field(description="最低薪资(k)")] = Field(None, description="最低薪资(k)")
    salary_max: Annotated[int | None, Field(description="最高薪资(k)")] = Field(None, description="最高薪资(k)")
    province: str = Field(..., description="省份")
    education: Annotated[str | None, Field(description="学历要求")] = Field(None, description="学历要求")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI助手回复内容")
    related_jobs: Annotated[list[RelatedJob] | None, Field(description="相关岗位推荐")] = None
