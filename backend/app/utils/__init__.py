"""业务异常与统一响应格式。"""
from typing import Any


class BusinessError(Exception):
    """业务规则冲突（如库存不足、状态不允许），message 直接展示给前端。"""

    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)


def ok(data: Any = None, message: str = "success") -> dict:
    """统一成功响应体。"""
    return {"code": 0, "message": message, "data": data}


def fail(message: str, code: int = 1) -> dict:
    """统一失败响应体（业务错误）。"""
    return {"code": code, "message": message, "data": None}