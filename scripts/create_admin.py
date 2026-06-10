#!/usr/bin/env python3
"""
创建管理员账号
首次部署时运行：python scripts/create_admin.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import init_db, get_db
from app.auth import create_user
from app.models import User
from app.logger import logger


def main():
    init_db()

    username = input("管理员用户名: ").strip()
    password = input("管理员密码: ").strip()
    email = input("邮箱（可选）: ").strip()

    if not username or not password:
        logger.error("用户名和密码不能为空")
        return

    with get_db() as db:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            logger.warning(f"用户已存在: {username}")
            return

    user = create_user(username, password, email, display_name="管理员")
    if user:
        with get_db() as db:
            u = db.query(User).filter(User.id == user.id).first()
            if u:
                u.is_admin = True
        logger.info(f"管理员账号创建成功: {username}")
    else:
        logger.error("创建失败")


if __name__ == "__main__":
    main()
