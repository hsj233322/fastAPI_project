# services/deepseek_service.py
import os
import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from typing import Annotated
from pydantic import Field

from schemas.ai_assistant import ChatMessage, RelatedJob
from crud.internship import search_internships 
from core.tool import Tool
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
            "你是实习帮助手，一个求职实习平台的智能助手。\n"
            "你的能力：\n"
            "1. 使用 search_jobs 工具搜索实习岗位，参数包括 keyword（关键词）、location（地点）、education（学历）。\n"
            "2. 使用 get_job_detail 工具获取某个岗位的详细信息，参数是 job_id。\n\n"
            "规则：\n"
            "- 仅当用户明确询问岗位或需要搜索岗位时才调用 search_jobs。\n"
            "- 如果用户询问某个具体岗位的详情，且你有该岗位的 id，调用 get_job_detail。\n"
            "- 如果第一次搜索没有结果，可以尝试放宽条件再搜一次，但最多搜索两次，避免过度调用。\n"
            "- 如果用户问平台功能、简历建议、面试技巧等，直接基于知识回答，不要调用工具。\n"
            "- 如果用户问无关内容，礼貌说明你只处理求职相关问题。\n"
            "- 始终使用中文，回答简洁专业，先陈述事实，再提供建议。\n"
            "- 如果工具返回错误，如实告知用户，不要编造信息。"
        )

    def _get_tools(self) -> list[dict[str, Any]]:
        """
        生成可供 OpenAI 模型调用的工具定义列表。

        此方法会在每次请求前被调用，将内部 Tool 对象序列化为 OpenAI 可识别的 JSON 结构（名字、描述、参数格式），
        使得模型能够根据用户问题选择合适的工具。
        """
        return [tool.to_openai_schema() for tool in self.tools]

    async def _call_deepseek_api(self, messages, tools=None):
        """
        调用 DeepSeek 模型，根据用户消息调用工具。
        """
        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            return None

        if tools:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                tools=tools,
                tool_choice="auto"
            )
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
        return response

    async def chat(
        self,
        db: AsyncSession,
        messages: list[dict[str, Any]],  # 传入时包含当前user消息（如果是多次调用，包含历史消息；如果是第一次调用，不包含历史消息），不包含system prompt
    ) -> tuple[str, list[RelatedJob], list[dict[str, Any]]]:
        """
        返回 (reply, related_jobs, updated_messages)
        updated_messages 为最终消息列表（不含 system prompt），用于保存会话。
        """
        system_prompt = self._get_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        related_jobs: list[RelatedJob] = []
        MAX_ITERATIONS = 5   # 最大迭代次数，避免无限循环

        # 循环调用模型，直到没有 tool_calls 或超过最大迭代次数
        for _ in range(MAX_ITERATIONS):
            response = await self._call_deepseek_api(full_messages, self._get_tools())
            if not response:
                return "AI服务暂时不可用，请稍后再试。", [], messages

            assistant_msg = response.choices[0].message # 获取模型回复的消息（可能包含 tool_calls 也可能只有纯文本）

            # 手动构造 assistant 消息
            assistant_dict: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_msg.content or "",
            }
            if assistant_msg.tool_calls:
                assistant_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_msg.tool_calls
                ]
            full_messages.append(assistant_dict) 

            # 同时保存到最终 messages（不含 system）
            messages.append(assistant_dict) 

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
                            if tool_name == "search_jobs" and isinstance(result, list):
                                # 收集岗位信息用于返回
                                related_jobs.extend(result)
                        except Exception as e: # AI 模型有时可能返回非标准 JSON 格式
                            logger.error(f"Tool execution error: {e}")
                            result = {"error": str(e)}

                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,   # 模型回复的 tool_call_id，用于关联数据库返回结果
                        "content": json.dumps(result, ensure_ascii=False),  # 数据库返回结果
                    }
                    full_messages.append(tool_msg)
                    messages.append(tool_msg) 

                continue  # 回到循环开头，让模型继续处理

            # 无工具调用，直接返回最终回复
            reply = assistant_msg.content or ""
            return reply, related_jobs, messages

        return "抱歉，我暂时无法完成这个任务，请稍后再试。", related_jobs, messages