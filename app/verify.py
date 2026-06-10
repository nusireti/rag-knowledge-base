"""
邮箱验证码模块
可选功能，默认关闭。启用需配置 SMTP。
"""

from __future__ import annotations

import random
import smtplib
import string
import time
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings
from app.logger import logger

# 验证码存储（生产环境应改用 Redis）
_codes: dict[str, dict] = {}


def generate_code(length: int = 6) -> str:
    """生成随机数字验证码"""
    return "".join(random.choices(string.digits, k=length))


def send_email(to: str, subject: str, body: str) -> bool:
    """发送邮件"""
    if not settings.SMTP_ENABLE:
        logger.warning("SMTP 未启用，无法发送邮件")
        return False

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = to

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
            s.starttls()
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)

        logger.info(f"邮件发送成功: {to}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def send_verify_code(email: str) -> bool:
    """发送验证码到指定邮箱"""
    code = generate_code()
    _codes[email] = {"code": code, "time": time.time()}

    body = f"""您的验证码是: {code}

验证码 5 分钟内有效，请勿泄露给他人。

—— RAG 知识库系统"""

    return send_email(email, "RAG 知识库 - 验证码", body)


def verify_code(email: str, code: str) -> bool:
    """验证验证码"""
    record = _codes.get(email)
    if not record:
        return False

    if time.time() - record["time"] > 300:  # 5 分钟过期
        del _codes[email]
        return False

    if record["code"] != code:
        return False

    del _codes[email]
    return True
