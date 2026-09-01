# services/deepseek_service.py
import os
import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from schemas.ai_assistant import RelatedJob
from core.tool import Tool
from services.tool_functions import search_jobs_by_semantic_func
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
                name="search_jobs_by_semantic",
                description=(
                    "根据用户的自然语言描述，通过语义匹配查找最相关的实习岗位，"
                    "并支持通过 location 参数对工作省份做精确过滤。"
                    "这是唯一用于搜索岗位的工具。无论用户是问'AI实习'、'广州的工作'还是'适合文科生的岗位'，都调用此工具。"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "用户的核心需求描述（岗位方向、专业、技能、学历等），不要包含地点信息",
                        },
                        "location": {
                            "type": "string",
                            "description": (
                                "期望的工作省份，如：河南、广东。"
                                "用户提到工作地点时必传，城市需转换为所属省份（如郑州→河南、深圳→广东）；"
                                "用户没有提到地点时省略此参数"
                            ),
                        },
                    },
                    "required": ["query"],
                },
                func=search_jobs_by_semantic_func,
            ),
        ]

    def _get_system_prompt(self) -> str:
        return (
            "你是实习帮助手，一个求职实习平台的智能助手。\n"
            "你的能力：\n"
            "1. 使用 search_jobs_by_semantic 工具搜索岗位。用户无论怎么描述（具体关键词或模糊意图），都调用此工具。\n\n"
            "规则：\n"
            "- 当用户询问岗位、推荐工作、或描述理想职位时，必须调用 search_jobs_by_semantic 工具。\n"
            "- 用户提到工作地点时，把地点转换为省份并传入 location 参数（如'郑州'→'河南'、'杭州'→'浙江'），query 中不要再重复地点；无法确定所属省份时省略 location。\n"
            "- 如果工具返回空列表，如实告知用户暂时没有匹配的岗位，并建议调整关键词或放宽条件，不要编造岗位。\n"
            "- 工具返回的结果已包含岗位标题、公司、薪资等详情，直接基于这些信息回答用户。\n"
            "- 如果用户问平台功能、简历建议、面试技巧等，直接基于知识回答，不要调用工具。\n"
            "- 如果用户问无关内容，礼貌说明你只处理求职相关问题。\n"
            "- 始终使用中文，回答简洁专业。"
        )

    def _get_tools(self) -> list[dict[str, Any]]:
        """
        生成可供 OpenAI 模型调用的工具定义列表。

        此方法会在每次请求前被调用，将内部 Tool 对象序列化为 OpenAI 可识别的 JSON 结构（名字、描述、参数格式），
        使得模型能够根据用户问题选择合适的工具。
        """
        return [tool.to_openai_schema() for tool in self.tools]

    async def _call_deepseek_api(
        self,
        messages,
        tools= None,
    ) -> Any:
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
        redis: Redis,
        messages: list[dict[str, Any]],  # 传入时包含当前user消息（如果是多次调用，包含历史消息；如果是第一次调用，不包含历史消息）
    ) -> tuple[str, list[RelatedJob], list[dict[str, Any]]]:
        """
        返回 (reply, related_jobs, messages)
        messages 为最终消息列表，用于保存会话。
        """
        system_prompt = self._get_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        related_jobs: list[RelatedJob] = []

        MAX_ITERATIONS = 5   # 最大迭代次数

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
                            # 执行工具函数
                            result = await tool.func(redis=redis, **args)
                
                            if isinstance(result, list):
                                related_jobs = result   # 向量检索到的top_k个岗位详情

                        except Exception as e: # AI 模型有时可能返回非标准 JSON 格式
                            logger.error(f"Tool execution error: {e}")
                            result = {"error": str(e)}

                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.id, 
                        "content": json.dumps(result, ensure_ascii=False), 
                    }
                    full_messages.append(tool_msg)
                    messages.append(tool_msg) 

                continue  # 回到循环开头，让模型继续处理

            # 无工具调用，直接返回最终回复
            reply = assistant_msg.content or ""
            return reply, related_jobs, messages

        return "抱歉，我暂时无法完成这个任务，请稍后再试。", related_jobs, messages