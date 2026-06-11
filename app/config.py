"""
应用配置
使用 pydantic-settings 从环境变量加载，支持 .env 文件
所有敏感信息和环境相关参数统一管理，不硬编码

安全要求：
- SECRET_KEY 必须通过环境变量或 .env 文件设置
- 生产环境 SECRET_KEY 至少 32 位随机字符
- 所有 API Key 通过环境变量注入，不硬编码
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，优先级：环境变量 > .env 文件 > 默认值"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- 应用基础 ----
    APP_NAME: str = "RAG Knowledge Base"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # SECRET_KEY: 必须通过环境变量或 .env 设置
    # 生产环境请使用: python -c "import secrets; print(secrets.token_hex(32))"
    # 生成一个 64 字符的随机十六进制字符串
    SECRET_KEY: str = ""

    # ---- 路径 ----
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"

    # ---- 数据库 ----
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'rag.db'}"
    DB_POOL_SIZE: int = 5
    DB_ECHO: bool = False

    # ---- 认证 ----
    AUTH_COOKIE_NAME: str = "rag_session"
    AUTH_SESSION_TTL_HOURS: int = 24
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5          # 连续失败次数限制
    LOGIN_LOCKOUT_MINUTES: int = 15      # 锁定时间（分钟）
    MIN_PASSWORD_LENGTH: int = 8         # 最小密码长度

    # ---- Embedding 模型 ----
    EMBEDDING_PROVIDER: Literal["local", "openai", "dashscope"] = "local"
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    DASHSCOPE_API_KEY: str = ""          # 通义/文心通过阿里云百炼接入

    # ---- LLM ----
    LLM_PROVIDER: Literal["local", "openai", "dashscope"] = "local"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    DASHSCOPE_LLM_MODEL: str = "qwen-plus"  # 通义千问
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048
    LLM_CONTEXT_WINDOW: int = 4096

    # ---- RAG ----
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_K: int = 6
    RETRIEVAL_SEARCH_TYPE: Literal["similarity", "mmr", "similarity_score_threshold"] = "similarity"
    USE_HYBRID_SEARCH: bool = True  # 是否使用 BM25+向量混合检索
    USE_RERANK: bool = False  # 是否使用 Cross-Encoder 重排序（较重，默认关闭）

    # ---- 邮件（用于验证码、找回密码） ----
    SMTP_ENABLE: bool = False  # 设为 True 启用邮件验证码
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""  # 你的邮箱
    SMTP_PASSWORD: str = ""  # SMTP 授权码（非邮箱密码）
    SMTP_FROM: str = ""  # 发件人地址

    # ---- 文档处理 ----
    MAX_UPLOAD_SIZE_MB: int = 50
    SUPPORTED_EXTENSIONS: list[str] = [".pdf", ".txt", ".md", ".docx"]

    # ---- 服务器 ----
    STREAMLIT_PORT: int = 8501
    STREAMLIT_SERVER_ADDRESS: str = "0.0.0.0"

    @property
    def data_dir(self) -> Path:
        """确保数据目录存在"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return self.DATA_DIR

    @property
    def vector_store_dir(self) -> Path:
        path = self.data_dir / "vector_store"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def documents_dir(self) -> Path:
        path = self.data_dir / "documents"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def conversations_dir(self) -> Path:
        path = self.data_dir / "conversations"
        path.mkdir(parents=True, exist_ok=True)
        return path


# 全局单例
settings = Settings()

# 确保数据目录存在
settings.data_dir

# ===================== 安全初始化校验 =====================

def _check_secret_key():
    """
    校验 SECRET_KEY 是否安全配置。

    - 如果 SECRET_KEY 为空，自动生成一个随机的并存入 .env
    - 如果 SECRET_KEY 为弱密钥（默认值/太短），给出警告
    - 生产环境建议手动设置强密钥
    """
    import sys

    if not settings.SECRET_KEY:
        # 自动生成 64 字符随机十六进制密钥
        auto_key = secrets.token_hex(32)
        settings.SECRET_KEY = auto_key

        # 尝试写入 .env 文件
        env_path = settings.BASE_DIR / ".env"
        try:
            existing = ""
            if env_path.exists():
                existing = env_path.read_text(encoding="utf-8")
            if "SECRET_KEY=" not in existing:
                with open(env_path, "a", encoding="utf-8") as f:
                    f.write(f"\n# 自动生成的密钥（建议替换为自定义密钥）\nSECRET_KEY={auto_key}\n")
                from app.logger import logger
                logger.info(f"已自动生成 SECRET_KEY 并写入 .env 文件")
        except Exception:
            pass

    elif len(settings.SECRET_KEY) < 32:
        import warnings
        warnings.warn(
            "⚠️ SECRET_KEY 长度不足 32 位，建议使用更长的随机密钥。\n"
            "可用以下命令生成: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    # 禁止使用默认密钥（安全红线）
    _DEFAULT_KEYS = [
        "change-this-to-a-random-secret-in-production",
        "rag-kb-secret-key-2026",
    ]
    if settings.SECRET_KEY in _DEFAULT_KEYS:
        settings.SECRET_KEY = secrets.token_hex(32)
        from app.logger import logger
        logger.warning(
            "检测到默认 SECRET_KEY，已自动替换为随机密钥。"
        )


# 执行安全校验
_check_secret_key()
