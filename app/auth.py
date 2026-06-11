"""
用户认证模块
bcrypt 密码哈希 + Session Token + 登录速率限制
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


# ===================== 登录速率限制 =====================

_login_attempts: dict[str, list] = {}
"""记录登录失败次数: {key: [timestamp, ...]}"""


def _rate_limit_key(username: str) -> str:
    """生成速率限制的 key（用户名 + IP 的哈希）"""
    raw = f"login:{username}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _check_rate_limit(username: str) -> bool:
    """
    检查登录是否被锁定。
    返回 True 表示允许继续，False 表示已锁定。
    """
    key = _rate_limit_key(username)
    now = time.time()
    lockout_window = settings.LOGIN_LOCKOUT_MINUTES * 60

    # 清理过期记录
    if key in _login_attempts:
        _login_attempts[key] = [
            t for t in _login_attempts[key]
            if now - t < lockout_window
        ]
        if len(_login_attempts[key]) >= settings.MAX_LOGIN_ATTEMPTS:
            # 检查最早的失败是否还在锁定窗口内
            elapsed = now - min(_login_attempts[key])
            if elapsed < lockout_window:
                remaining = int(lockout_window - elapsed)
                logger.warning(f"登录已被锁定（剩余 {remaining} 秒）: {username}")
                return False
            # 锁定窗口已过，重置
            _login_attempts[key] = []
    return True


def _record_failed_attempt(username: str):
    """记录一次失败的登录尝试"""
    key = _rate_limit_key(username)
    if key not in _login_attempts:
        _login_attempts[key] = []
    _login_attempts[key].append(time.time())
    # 限制内存使用：最多保留最近 100 条
    if len(_login_attempts[key]) > 100:
        _login_attempts[key] = _login_attempts[key][-50:]


def _clear_rate_limit(username: str):
    """登录成功后清除失败记录"""
    key = _rate_limit_key(username)
    _login_attempts.pop(key, None)


# ===================== 密码策略 =====================

def validate_password(password: str) -> tuple[bool, str]:
    """
    密码强度校验。
    返回 (是否通过, 错误消息)。
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False, f"密码至少需要 {settings.MIN_PASSWORD_LENGTH} 个字符"

    if len(password) > 128:
        return False, "密码不能超过 128 个字符"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper or has_lower) or not has_digit:
        return False, "密码需要包含字母和数字"

    # 检查常见弱密码
    _common = ["12345678", "password", "admin123", "123456789", "qwerty123"]
    if password.lower() in _common:
        return False, "密码过于常见，请使用更强的密码"

    return True, ""


# ===================== 密码哈希 =====================

def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, AttributeError) as e:
        logger.error(f"密码验证失败: {e}")
        return False


# ===================== 用户管理 =====================

def create_user(
    username: str, password: str,
    email: str = "", display_name: str = "",
) -> Optional[User]:
    """创建新用户（带输入校验）"""
    # 校验用户名
    username = username.strip()
    if not username or len(username) < 2:
        logger.warning("创建用户失败: 用户名太短")
        return None
    if len(username) > 32:
        logger.warning("创建用户失败: 用户名太长")
        return None
    if not username.replace("_", "").replace("-", "").isalnum():
        logger.warning("创建用户失败: 用户名含非法字符")
        return None

    # 校验密码
    valid, msg = validate_password(password)
    if not valid:
        logger.warning(f"创建用户失败: {msg}")
        return None

    # 校验邮箱（可选）
    if email and ("@" not in email or "." not in email):
        logger.warning("创建用户失败: 邮箱格式不正确")
        return None

    with get_db() as db:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            logger.warning(f"创建用户失败: 用户已存在")
            return None

        if email:
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                logger.warning(f"创建用户失败: 邮箱已被使用")
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
    """验证用户登录（含速率限制）"""
    username = username.strip()

    # 速率限制检查
    if not _check_rate_limit(username):
        return None

    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            _record_failed_attempt(username)
            logger.warning(f"登录失败: 用户不存在")
            return None

        if not user.is_active:
            _record_failed_attempt(username)
            logger.warning(f"登录失败: 用户已禁用")
            return None

        if not verify_password(password, user.password_hash):
            _record_failed_attempt(username)
            remaining = settings.MAX_LOGIN_ATTEMPTS - len(_login_attempts.get(
                _rate_limit_key(username), []
            ))
            logger.warning(f"登录失败: 密码错误（还可尝试 {remaining} 次）")
            return None

        # 登录成功，清除失败记录
        _clear_rate_limit(username)
        user.last_login_at = datetime.now(timezone.utc)
        db.flush()
        logger.info(f"登录成功: {username}")
        return user


def get_user_by_id(user_id: str) -> Optional[User]:
    """根据 ID 获取用户"""
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(username: str) -> Optional[User]:
    """根据用户名获取用户"""
    with get_db() as db:
        return db.query(User).filter(User.username == username).first()


# ===================== Session Token =====================

def _sign_token(payload: str) -> str:
    """使用 BLAKE2b 签名（比 SHA256 更快更安全）"""
    return hashlib.blake2b(
        settings.SECRET_KEY.encode("utf-8") + payload.encode("utf-8"),
        digest_size=16,
    ).hexdigest()


def create_session(user_id: str) -> str:
    """
    创建登录 Session Token。
    格式: v2.{user_id}.{timestamp}.{random}.{signature}
    """
    timestamp = str(int(time.time()))
    random_part = secrets.token_hex(8)
    payload = f"{user_id}.{timestamp}.{random_part}"
    signature = _sign_token(payload)
    return f"v2.{payload}.{signature}"


def validate_session(token: str) -> Optional[str]:
    """
    验证 Session Token。
    返回 user_id 或 None。
    """
    try:
        parts = token.split(".")
        if len(parts) == 4 and parts[0] == "v2":
            # v2 格式: v2.{user_id}.{timestamp}.{random}.{signature}
            _, user_id, timestamp, random_part, signature = parts
            payload = f"{user_id}.{timestamp}.{random_part}"
        else:
            return None

        # 验证签名（恒定时间比较）
        expected_sig = _sign_token(payload)
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
