"""
应用配置
使用 pydantic-settings 从环境变量加载，支持 .env 文件
所有敏感信息和环境相关参数统一管理，不硬编码
"""

from __future__ import annotations

import os
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
    SECRET_KEY: str = "change-this-to-a-random-secret-in-production"

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

    # ---- Embedding 模型 ----
    EMBEDDING_PROVIDER: Literal["local", "openai"] = "local"
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ---- LLM ----
    LLM_PROVIDER: Literal["local", "openai"] = "local"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
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
