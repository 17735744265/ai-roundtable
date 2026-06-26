"""Custom exceptions and global exception handler."""

from fastapi import Request
from fastapi.responses import JSONResponse
from app.schemas.common import ApiResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code


class ValidationException(AppException):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)
        self.detail = detail


class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code="SESSION_NOT_FOUND", status_code=404)


class ConflictException(AppException):
    def __init__(self, message: str = "会话正在进行中，无法操作"):
        super().__init__(message, code="SESSION_IN_PROGRESS", status_code=409)


class LLMAPIException(AppException):
    def __init__(self, message: str = "LLM API 调用失败"):
        super().__init__(message, code="LLM_API_ERROR", status_code=500)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            code=1,
            message=exc.code,
            data={"detail": exc.message, **(getattr(exc, "detail", None) or {})},
        ).model_dump(),
    )
