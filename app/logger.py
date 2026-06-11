"""
结构化日志系统
生产环境输出 JSON 格式，开发环境输出可读格式
"""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys
from pathlib import Path

from app.config import settings


# 敏感字段列表（日志中自动脱敏）
SENSITIVE_FIELDS = [
    "password", "secret", "token", "auth", "key", "api_key",
    "api_secret", "access_key", "private_key", "credential",
]

# 常见敏感数据模式
SENSITIVE_PATTERNS = [
    (r'(?i)(password["\s]*[:=]\s*["\']?)[^"\'\s,;}]+', r'\1****'),
    (r'(?i)(secret.*?["\s]*[:=]\s*["\']?)[^"\'\s,;}]+', r'\1****'),
    (r'(?i)(token["\s]*[:=]\s*["\']?)[^"\'\s,;}]+', r'\1****'),
    (r'(?i)(api_key["\s]*[:=]\s*["\']?)[^"\'\s,;}]+', r'\1****'),
    (r'(?i)(sk-[a-zA-Z0-9]{20,})', r'sk-****'),
    (r'(?i)(ghp_[a-zA-Z0-9]{20,})', r'ghp_****'),
    (r'(?i)(gho_[a-zA-Z0-9]{20,})', r'gho_****'),
]


def sanitize_message(msg: str) -> str:
    """对日志消息中的敏感内容进行脱敏处理"""
    for pattern, replacement in SENSITIVE_PATTERNS:
        msg = re.sub(pattern, replacement, msg)
    return msg


class SanitizedFormatter(logging.Formatter):
    """自动脱敏的日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        original = record.msg
        try:
            record.msg = sanitize_message(str(record.msg))
            return super().format(record)
        finally:
            record.msg = original


def setup_logging(name: str = "rag") -> logging.Logger:
    """
    配置并返回应用日志器

    特点：
        - 自动对密码、token、API Key 等敏感信息脱敏
        - 文件轮转，防止日志无限增长
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    logger.handlers.clear()

    formatter = SanitizedFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stdout 输出
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 文件输出（仅非 Docker 环境）
    if not Path("/.dockerenv").exists():
        log_dir = settings.data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 全局日志器实例
logger = setup_logging()
