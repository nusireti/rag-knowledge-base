"""
用户认证模块
使用 bcrypt 密码哈希 + 简单 Session Token 实现
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

import bcrypt

from app.config import settings
from app.database import get_db
from app.logger import logger
from app.models import User


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码（自动生成 salt）"""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码与哈希是否匹配"""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, AttributeError) as e:
        logger.error(f"密码验证失败: {e}")
        return False


def create_user(username: str, password: str, email: str = "", display_name: str = "") -> Optional[User]:
    """创建新用户"""
    if not username or len(username) < 2:
        logger.warning("用户名太短")
        return None

    if len(password) < 6:
        logger.warning("密码太短")
        return None

    with get_db() as db:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            logger.warning(f"用户已存在: {username}")
            return None

        user = User(
            username=username,
            email=email or None,
            display_name=display_name or username,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()
        db.refresh(user)
        logger.info(f"创建用户成功: {username}")
        return user


def authenticate_user(username: str, password: str) -> Optional[User]:
    """验证用户登录"""
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.warning(f"登录失败，用户不存在: {username}")
            return None

        if not user.is_active:
            logger.warning(f"登录失败，用户已禁用: {username}")
            return None

        if not verify_password(password, user.password_hash):
            logger.warning(f"登录失败，密码错误: {username}")
            return None

        user.last_login_at = datetime.now(timezone.utc)
        db.flush()
        logger.info(f"用户登录成功: {username}")
        return user


def get_user_by_id(user_id: str) -> Optional[User]:
    """根据 ID 获取用户"""
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(username: str) -> Optional[User]:
    """根据用户名获取用户"""
    with get_db() as db:
        return db.query(User).filter(User.username == username).first()


# ---- Session Token 管理 ----
# 简化方案：用 HMAC 签名 token 替代 JWT，避免额外依赖


def _sign_payload(payload: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]


def create_session(user_id: str) -> str:
    """
    创建登录 Session Token

    格式: {user_id}.{timestamp}.{signature}
    """
    timestamp = str(int(time.time()))
    payload = f"{user_id}.{timestamp}"
    signature = _sign_payload(payload)
    return f"{payload}.{signature}"


def validate_session(token: str) -> Optional[str]:
    """
    验证 Session Token

    返回 user_id 或 None
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        user_id, timestamp, signature = parts

        # 验证签名
        payload = f"{user_id}.{timestamp}"
        expected_sig = _sign_payload(payload)
        if not hmac.compare_digest(signature, expected_sig):
            return None

        # 检查过期
        token_time = int(timestamp)
        now = int(time.time())
        if now - token_time > settings.AUTH_SESSION_TTL_HOURS * 3600:
            return None

        return user_id
    except (ValueError, IndexError) as e:
        logger.error(f"Session 验证失败: {e}")
        return None
