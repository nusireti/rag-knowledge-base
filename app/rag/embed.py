"""
Embedding 模型管理
全局单例 + 懒加载，确保模型只加载一次
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.config import settings
from app.logger import logger


def _get_provider() -> str:
    """获取当前 Embedding 提供商（优先级：环境变量 > 配置文件）"""
    return os.environ.get("EMBEDDING_PROVIDER", settings.EMBEDDING_PROVIDER)


# 全局缓存
_embedding_model = None


def get_embedding_model():
    """
    获取 Embedding 模型实例（全局缓存，只加载一次）

    支持 local（HuggingFace）和 openai 两种 provider
    """
    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    provider = _get_provider()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("EMBEDDING_PROVIDER=openai 但未设置 OPENAI_API_KEY")
        from langchain_openai import OpenAIEmbeddings
        _embedding_model = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        logger.info("使用 OpenAI Embedding")

    elif provider == "dashscope":
        if not settings.DASHSCOPE_API_KEY:
            raise RuntimeError("EMBEDDING_PROVIDER=dashscope 但未设置 DASHSCOPE_API_KEY")
        from langchain_openai import OpenAIEmbeddings
        _embedding_model = OpenAIEmbeddings(
            model="text-embedding-v3",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            openai_api_key=settings.DASHSCOPE_API_KEY,
        )
        logger.info("使用 DashScope/通义 Embedding")

    elif provider == "deepseek":
        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("EMBEDDING_PROVIDER=deepseek 但未设置 DEEPSEEK_API_KEY")
        from langchain_openai import OpenAIEmbeddings
        _embedding_model = OpenAIEmbeddings(
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com",
            openai_api_key=settings.DEEPSEEK_API_KEY,
        )
        logger.info("使用 DeepSeek Embedding")

    else:
        os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
        from langchain_huggingface import HuggingFaceEmbeddings
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.LOCAL_EMBEDDING_MODEL,
            model_kwargs={"device": "cpu", "local_files_only": True},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info(f"使用本地 Embedding: {settings.LOCAL_EMBEDDING_MODEL}")

    return _embedding_model


def clear_embedding_cache():
    """清空缓存（知识库重建时调用）"""
    global _embedding_model
    _embedding_model = None
    logger.debug("Embedding 缓存已清空")
