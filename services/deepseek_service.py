import os
import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from typing import Annotated

from schemas.ai_assistant import ChatMessage, RelatedJob
from crud.internship import search_internships 

logger = logging.getLogger(__name__)


class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = "deepseek-v4-flash" 

        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not configured")

    def _get_system_prompt(self) -> str:
        return (
            "你是一个求职实习平台的智能助手，名叫'实习帮助手'。\n"
            "你可以调用 search_jobs 工具查询数据库中的实习岗位。\n"
            "如果用户问的是平台功能（如何收藏、如何看历史），直接回答。\n"
            "如果用户问的是简历、面试等通用建议，基于你的知识回答。\n"
            "如果用户问的是天气、新闻等无关内容，礼貌说明你只处理求职相关问题。\n"
            "始终使用中文，回答简洁专业。"
        )

    def _get_tools(self) -> Annotated[list[dict[str, Any]], "需要传递的工具定义（符合 OpenAI 函数调用格式）"]:
        return [{
            "type": "function",
            "function": {
                "name": "search_jobs",
                "description": "根据关键词、地点、学历要求搜索实习岗位。仅当用户明确问岗位时才调用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "岗位名称关键词，如'开发'、'算法'、'产品'"
                        },
                        "location": {
                            "type": "string",
                            "description": "省份或城市，如'北京'、'上海'"
                        },
                        "education": {
                            "type": "string",
                            "description": "学历要求，如'本科'、'硕士'"
                        }
                    },
                    "required": []
                }
            }
        }]

    async def _call_deepseek_api(
        self,
        messages: Annotated[list[dict[str, str]], "对话消息历史，格式为 [{\"role\": \"user\", \"content\": \"...\"}]"],
        tools: Annotated[list[dict[str, Any]] | None, "需要传递的工具定义（可选），符合 OpenAI 函数调用格式"] = None
    ) -> Annotated[dict[str, Any] | None, "DeepSeek API 响应"]:
        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return None

            return response.json()

        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            return None

    async def chat(
        self,
        db: AsyncSession,
        message: str,
        conversation_history: Annotated[list[ChatMessage] | None, "对话消息历史"] = None,
    ) -> tuple[str, list[RelatedJob]]:
        messages: Annotated[list[dict[str, str]], "对话消息历史，格式为 [{\"role\": \"user\", \"content\": \"...\"}]"] = []
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        # 第一轮：带 tools
        response = await self._call_deepseek_api(messages, self._get_tools())

        if not response:
            return "AI服务暂时不可用，请稍后再试。", []

        choice = response["choices"][0]
        finish_reason = choice.get("finish_reason")

        # LLM 决定调用工具
        if finish_reason == "tool_calls":
            tool_call = choice["message"]["tool_calls"][0]
            try:
                args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            # 执行查询（使用新增的 search_internships 函数）
            jobs = await search_internships(
                db,
                keyword=args.get("keyword"),
                location=args.get("location"),
                education=args.get("education"),
                limit=8,
            )

            # 追加 assistant 的 tool_calls 消息
            messages.append(choice["message"])

            # 构造返回数据
            job_list = []
            for job in jobs:
                job_list.append({
                    "id": job.id,
                    "title": job.title,
                    "company_name": job.company_name,
                    "province": job.province,
                    "education": job.education,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(job_list, ensure_ascii=False),
            })

            # 第二轮：不带 tools，生成最终回答
            final_response = await self._call_deepseek_api(messages, tools=None)
            if not final_response:
                return "AI服务暂时不可用，请稍后再试。", []

            reply = final_response["choices"][0]["message"]["content"]
            related_schemas = [RelatedJob.model_validate(job) for job in jobs]
            return reply, related_schemas

        else:
            # 闲聊直接返回
            reply = choice["message"]["content"]
            return reply, []