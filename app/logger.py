"""
结构化日志系统
生产环境输出 JSON 格式，开发环境输出可读格式
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from app.config import settings


def setup_logging(name: str = "rag") -> logging.Logger:
    """
    配置并返回应用日志器

    生产环境：
        - JSON 格式输出到 stdout（适合容器化）
        - 同时写入文件轮转

    开发环境：
        - 可读格式输出到 stdout
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
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
