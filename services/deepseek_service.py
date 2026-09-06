# services/deepseek_service.py
import os
import json
import logging
from typing import Any

from redis.asyncio import Redis
from openai import AsyncOpenAI

from schemas.ai_assistant import RelatedJob
from core.tool_context import ToolContext
from core.tool_errors import (
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolParamError,
)
from core.tool_registry import default_registry
# 导入工具模块以触发 @tool 装饰器注册
import services.tool_functions  # noqa: F401

logger = logging.getLogger(__name__)


class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = "deepseek-v4-flash"
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not configured")

        # 工具从全局注册表获取
        self.registry = default_registry

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
        """从注册表获取所有工具的 OpenAI schema。"""
        return self.registry.get_schemas()

    async def _call_deepseek_api(
        self,
        messages,
        tools=None,
    ) -> Any:
        """调用 DeepSeek 模型，根据用户消息调用工具。"""
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
        ctx: ToolContext,
        messages: list[dict[str, Any]],
    ) -> tuple[str, list[RelatedJob], list[dict[str, Any]]]:
        """
        返回 (reply, related_jobs, messages)
        messages 为最终消息列表，用于保存会话。
        """
        system_prompt = self._get_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        related_jobs: list[RelatedJob] = []

        MAX_ITERATIONS = 5

        for _ in range(MAX_ITERATIONS):
            response = await self._call_deepseek_api(full_messages, self._get_tools())
            if not response:
                return "AI服务暂时不可用，请稍后再试。", [], messages

            assistant_msg = response.choices[0].message

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
            messages.append(assistant_dict)

            if assistant_msg.tool_calls:
                for tool_call in assistant_msg.tool_calls:
                    tool_name = tool_call.function.name
                    tool = self.registry.get(tool_name)

                    if not tool:
                        available = [t.name for t in self.registry.get_all()]
                        result = ToolNotFoundError(
                            f"工具 '{tool_name}' 不存在。当前可用工具: {available}。"
                        ).to_result()
                    else:
                        try:
                            args = json.loads(tool_call.function.arguments or "{}")
                            # 统一执行入口：内部完成参数校验 + 异常分级
                            result = await tool.execute(ctx, args)

                            if isinstance(result, list):
                                related_jobs = result

                        except ToolError as e:
                            # 工具异常统一转为结构化结果返回给 LLM
                            result = e.to_result()
                            logger.warning(f"工具 {tool_name} 执行异常: {e}")
                        except json.JSONDecodeError as e:
                            result = ToolParamError(f"参数 JSON 解析失败: {e}").to_result()

                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                    full_messages.append(tool_msg)
                    messages.append(tool_msg)

                continue

            # 无工具调用，直接返回最终回复
            reply = assistant_msg.content or ""
            return reply, related_jobs, messages

        return "抱歉，我暂时无法完成这个任务，请稍后再试。", related_jobs, messages
