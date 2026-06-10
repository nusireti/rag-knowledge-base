#!/usr/bin/env python3
"""
初始化数据库
首次部署时运行：python scripts/init_db.py
"""

import sys
import os

# 确保能找到 app 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import init_db
from app.config import settings
from app.logger import logger


def main():
    """创建数据库表结构"""
    logger.info(f"初始化数据库: {settings.DATABASE_URL}")
    init_db()
    logger.info("数据库初始化完成")


if __name__ == "__main__":
    main()
