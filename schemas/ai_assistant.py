from pydantic import BaseModel, Field
from typing import List, Optional
from schemas import BaseSchema


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：user 或 assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户提问内容")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None, description="历史对话记录"
    )


class RelatedJob(BaseSchema):
    id: int = Field(..., description="岗位ID")
    title: str = Field(..., description="岗位名称")
    company_name: str = Field(..., description="公司名称")
    salary_min: Optional[int] = Field(None, description="最低薪资(k)")
    salary_max: Optional[int] = Field(None, description="最高薪资(k)")
    province: str = Field(..., description="省份")
    education: Optional[str] = Field(None, description="学历要求")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI助手回复内容")
    related_jobs: Optional[List[RelatedJob]] = Field(
        default=None, description="相关岗位推荐"
    )