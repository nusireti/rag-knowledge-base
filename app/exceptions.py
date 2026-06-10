"""
自定义异常和全局错误处理
确保所有错误都可追溯、可分类，不给用户暴露原始堆栈
"""

from __future__ import annotations


class RAGException(Exception):
    """应用基础异常"""
    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "服务器内部错误"

    def __init__(self, message: str = None, details: dict = None):
        self.message = message or self.message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error": self.code,
            "message": self.message,
            "status": self.status_code,
        }


class AuthenticationError(RAGException):
    code = "AUTH_FAILED"
    status_code = 401
    message = "认证失败，请重新登录"


class AuthorizationError(RAGException):
    code = "FORBIDDEN"
    status_code = 403
    message = "没有权限执行此操作"


class NotFoundError(RAGException):
    code = "NOT_FOUND"
    status_code = 404
    message = "请求的资源不存在"


class ValidationError(RAGException):
    code = "VALIDATION_ERROR"
    status_code = 422
    message = "请求参数验证失败"


class RateLimitError(RAGException):
    code = "RATE_LIMIT"
    status_code = 429
    message = "请求过于频繁，请稍后再试"


class FileTooLargeError(RAGException):
    code = "FILE_TOO_LARGE"
    status_code = 413
    message = "文件大小超过限制"


class UnsupportedFileTypeError(RAGException):
    code = "UNSUPPORTED_FILE_TYPE"
    status_code = 415
    message = "不支持的文件格式"


class RAGEngineError(RAGException):
    code = "RAG_ENGINE_ERROR"
    status_code = 500
    message = "知识库引擎处理出错"


class DatabaseError(RAGException):
    code = "DATABASE_ERROR"
    status_code = 500
    message = "数据库操作失败"
