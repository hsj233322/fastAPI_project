# services/deepseek_service.py
import os
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI

from core.tool_context import ToolContext
from core.tool_errors import (
    ToolError,
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
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
        self.temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "1024"))

        # 构造异步客户端
        self.client = (
            AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            if self.api_key else None
        )

        # 全局注册表获取工具
        self.registry = default_registry


    def _get_system_prompt(self) -> str:
        return (
            "你是一个求职实习平台的智能助手。\n"
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


    async def _stream_deepseek_api(self, messages, tools=None):
        """调用 DeepSeek 模型（流式），返回异步流迭代器。"""
        assert self.client is not None, "client 未初始化"  # 收窄类型，确保客户端存在

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "stream": True,
            "reasoning_effort": "low",
            "extra_body": {"thinking": {"type": "enabled"}},
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        return await self.client.chat.completions.create(**kwargs)

    @staticmethod
    def _build_assistant_dict(
        content: str,
        tool_calls: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """根据内容与（已拼装完整的）工具调用构造 assistant 消息，用于写回会话历史。"""
        assistant_dict: dict[str, Any] = {
            "role": "assistant",
            "content": content,
        }
        if tool_calls:
            assistant_dict["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
                for tc in tool_calls
            ]
        return assistant_dict

    async def _execute_tool_calls(
        self,
        ctx: ToolContext,
        tool_calls: list[dict[str, str]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        执行一批工具调用，返回 (tool 消息列表, 相关岗位)。
        tool_calls 中每项为已拼装完整的 {id, name, arguments}。
        供流式 chat_stream 的 Agent 循环调用。
        """
        tool_messages: list[dict[str, Any]] = []
        related_jobs: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool = self.registry.get(tool_name)

            if not tool:
                available = [t.name for t in self.registry.get_all()]
                result = ToolNotFoundError(
                    f"工具 '{tool_name}' 不存在。当前可用工具: {available}。"
                ).to_result()
            else:
                try:
                    args = json.loads(tool_call["arguments"] or "{}")
                    # 统一执行入口：内部完成参数校验 + 异常分级
                    result = await tool.execute(ctx, args)

                    if isinstance(result, list):
                        related_jobs.extend(result)

                except ToolError as e:
                    # 工具异常统一转为结构化结果返回给 LLM
                    result = e.to_result()
                    logger.warning(f"工具 {tool_name} 执行异常: {e}")
                except json.JSONDecodeError as e:
                    result = ToolParamError(f"参数 JSON 解析失败: {e}").to_result()

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })

        return tool_messages, related_jobs

    # 流式 SSE 事件类型：
    #   {"type": "reasoning", "content": "..."}  思考过程增量
    #   {"type": "status",    "content": "..."}  工具轮提示
    #   {"type": "delta",     "content": "..."}  正文增量
    #   {"type": "jobs",      "content": [...]}  相关岗位
    #   {"type": "error",     "content": "..."}  错误
    # 会话消息通过对传入 messages 的原地 append/extend 累积，
    # 路由层在流正常结束后直接拿该列表落库（async generator 无法 return 值）。
    async def chat_stream(
        self,
        ctx: ToolContext,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[dict[str, Any], None]:
        system_prompt = self._get_system_prompt()
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        MAX_ITERATIONS = 5

        try:
            for _ in range(MAX_ITERATIONS):
                content_parts: list[str] = []
                # 工具调用按 index 分片到达，需分别累积 id / name / arguments
                tool_acc: dict[int, dict[str, str]] = {}

                stream = await self._stream_deepseek_api(
                    full_messages, self._get_tools()
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    # 先判断是否有思考内容
                    if delta.reasoning_content:
                        yield {"type": "reasoning", "content": delta.reasoning_content}

                    # 再判断正文内容
                    if delta.content:
                        content_parts.append(delta.content)
                        yield {"type": "delta", "content": delta.content}

                    # 再判断工具调用
                    if delta.tool_calls:
                        for piece in delta.tool_calls:
                            # 如果index不存在，初始化一个空字典,否则直接获取对应的字典
                            slot = tool_acc.setdefault(
                                piece.index,
                                {"id": "", "name": "", "arguments": ""},
                            )
                            if piece.id:
                                slot["id"] = piece.id
                            fn = piece.function
                            if fn:
                                if fn.name:
                                    slot["name"] += fn.name
                                if fn.arguments:
                                    slot["arguments"] += fn.arguments

                # 排序工具调用，确保按 index 顺序
                tool_calls = [tool_acc[i] for i in sorted(tool_acc)]
                assistant_dict = self._build_assistant_dict(
                    "".join(content_parts), tool_calls or None
                )
                # 原地写回：full_messages 用于本轮 Agent 循环，messages 用于落库
                full_messages.append(assistant_dict)
                messages.append(assistant_dict)

                if tool_calls:
                    # 工具轮：模型正文通常为空，不下发 tool_calls 碎片，仅给一个状态提示
                    yield {"type": "status", "content": "正在为你搜索相关岗位，请稍候…"}
                    tool_messages, jobs = await self._execute_tool_calls(ctx, tool_calls)
                    if jobs:
                        # 岗位检索到即下发，前端可在正文生成的同时渲染卡片
                        yield {"type": "jobs", "content": jobs}
                    full_messages.extend(tool_messages)
                    messages.extend(tool_messages)
                    continue

                # 无工具调用：本轮即最终回复，正文已逐片下发，直接结束
                return

            # 超过最大迭代次数仍未收敛，给用户一个兜底文案
            yield {"type": "delta", "content": "抱歉，我暂时无法完成这个任务，请稍后再试。"}
        except Exception:
            logger.exception("流式对话失败")
            yield {"type": "error", "content": "AI服务暂时不可用，请稍后再试。"}
