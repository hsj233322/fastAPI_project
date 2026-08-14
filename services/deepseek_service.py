# services/deepseek_service.py
import os
import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from typing import Annotated

from schemas.ai_assistant import ChatMessage, RelatedJob
from crud.internship import search_internships 
from tools import Tool
from services.tool_functions import search_jobs_func, get_job_detail_func
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = "deepseek-v4-flash" 
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not configured")
        
        self.tools = [
            Tool(
                name="search_jobs",
                description="根据关键词、地点、学历要求搜索实习岗位。仅当用户明确问岗位时才调用。",
                parameters={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "岗位名称关键词，如'开发'、'算法'、'产品'"},
                        "location": {"type": "string", "description": "省份或城市，如'北京'、'上海'"},
                        "education": {"type": "string", "description": "学历要求，如'本科'、'硕士'"},
                    },
                    "required": [],
                },
                func=search_jobs_func,
            ),
            Tool(
                name="get_job_detail",
                description="根据岗位ID获取岗位详细信息。当用户想了解某个具体岗位详情时调用。",
                parameters={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "integer", "description": "岗位ID"},
                    },
                    "required": ["job_id"],
                },
                func=get_job_detail_func,
            ),
        ]

    def _get_system_prompt(self) -> str:
        return (
            "你是一个求职实习平台的智能助手，名叫'实习帮助手'。\n"
            "你可以调用以下工具：\n"
            "1. search_jobs：根据关键词、地点、学历搜索实习岗位。\n"
            "2. get_job_detail：根据岗位ID获取岗位详情。\n"
            "如果用户问平台功能，直接回答。\n"
            "如果用户问简历、面试建议，基于知识回答。\n"
            "如果用户问无关内容，礼貌说明只处理求职相关问题。\n"
            "始终使用中文，回答简洁专业。"
        )

    def _get_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self.tools]

    async def _call_deepseek_api(self, messages, tools=None):
        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            return None

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            return None

    async def chat(
        self,
        db: AsyncSession,
        message: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> tuple[str, list[RelatedJob]]:
        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        related_jobs = []
        MAX_ITERATIONS = 5

        for _ in range(MAX_ITERATIONS):
            response = await self._call_deepseek_api(messages, self._get_tools())
            if not response:
                return "AI服务暂时不可用，请稍后再试。", []

            choice = response["choices"][0]
            assistant_msg = choice.message

            # 将 assistant 消息转为 dict 放入 messages
            messages.append(assistant_msg.model_dump())

            if assistant_msg.tool_calls:
                for tool_call in assistant_msg.tool_calls:
                    tool_name = tool_call.function.name
                    tool = next((t for t in self.tools if t.name == tool_name), None)

                    if not tool:
                        result = {"error": f"未知工具: {tool_name}"}
                    else:
                        try:
                            args = json.loads(tool_call.function.arguments or "{}")
                            result = await tool.func(db=db, **args)
                            if tool_name == "search_jobs":
                                # 收集岗位信息用于返回
                                related_jobs.extend(result)
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            result = {"error": str(e)}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                continue  # 回到循环开头，让模型继续思考

            # 没有 tool_calls，直接返回文本
            reply = assistant_msg.content or ""
            return reply, related_jobs

        return "抱歉，我暂时无法完成这个任务，请稍后再试。", related_jobs