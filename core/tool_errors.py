# core/tool_errors.py
from typing import Any


class ToolError(Exception):
    """工具执行错误基类，所有工具异常都继承自此"""

    def to_result(self) -> dict[str, Any]:
        return {"error": self.__class__.__name__, "message": str(self)}


class ToolNotFoundError(ToolError):
    """LLM 调用了不存在的工具"""


class ToolParamError(ToolError):
    """参数校验失败，LLM 应修正参数后重试"""


class ToolExecutionError(ToolError):
    """执行失败（如数据库超时），可根据 retryable 判断是否重试"""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable

    def to_result(self) -> dict[str, Any]:
        result = super().to_result()
        result["retryable"] = self.retryable
        return result


class ToolTimeoutError(ToolExecutionError):
    def __init__(self):
        super().__init__("工具执行超时，请稍后重试", retryable=True)
