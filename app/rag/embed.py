"""
Embedding 模型管理
全局单例 + 懒加载，确保模型只加载一次
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.config import settings
from app.logger import logger


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

    if settings.EMBEDDING_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("EMBEDDING_PROVIDER=openai 但未设置 OPENAI_API_KEY")
        from langchain_openai import OpenAIEmbeddings
        _embedding_model = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        logger.info("使用 OpenAI Embedding")
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
