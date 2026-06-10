"""
文档导入管道
加载 -> 切分 -> 向量化 -> 存储
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Set

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import settings
from app.logger import logger
from app.rag.embed import get_embedding_model, clear_embedding_cache
from app.rag.loaders import load_document


def split_documents(documents: List[Document]) -> List[Document]:
    """
    将文档切分为小块

    使用 RecursiveCharacterTextSplitter，按自然段落边界切分
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"文档切分: {len(documents)} 段 -> {len(chunks)} 块")
    return chunks


def build_vector_store(
    chunks: List[Document],
    vector_dir: str,
    overwrite: bool = False,
) -> Chroma:
    """
    创建/重建向量数据库

    参数:
        chunks: 切分后的文档块
        vector_dir: 向量数据库存储路径
        overwrite: 是否覆盖已有数据
    """
    vec_path = Path(vector_dir)

    if overwrite and vec_path.exists():
        shutil.rmtree(vec_path)
        logger.info(f"已清除旧向量库: {vector_dir}")

    embedding = get_embedding_model()
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=vector_dir,
    )
    logger.info(f"向量库创建完成: {len(chunks)} 个向量")
    return vector_store


def load_all_documents(docs_dir: str) -> List[Document]:
    """
    加载目录下所有支持的文档

    自动去重（Windows 大小写不敏感）
    每种格式异常隔离，一个文件失败不影响其他
    """
    doc_dir = Path(docs_dir)
    if not doc_dir.exists():
        logger.warning(f"文档目录不存在: {doc_dir}")
        return []

    all_docs: List[Document] = []
    seen: Set[str] = set()

    for ext in settings.SUPPORTED_EXTENSIONS:
        for file_path in sorted(doc_dir.glob(f"*{ext}")):
            abs_path = str(file_path.resolve())
            if abs_path in seen:
                continue
            seen.add(abs_path)

            docs = load_document(abs_path)
            all_docs.extend(docs)

    logger.info(f"文档加载完成: {len(all_docs)} 段 (来自 {len(seen)} 个文件)")
    return all_docs


def ingest_documents(
    docs_dir: str = None,
    vector_dir: str = None,
    overwrite: bool = True,
) -> int:
    """
    完整导入管道：加载 -> 切分 -> 向量化 -> 存储

    参数:
        docs_dir: 文档目录（默认使用配置路径）
        vector_dir: 向量库目录（默认使用配置路径）
        overwrite: 是否覆盖已有向量库

    返回:
        向量数量，失败返回 0
    """
    docs_dir = docs_dir or str(settings.documents_dir)
    vector_dir = vector_dir or str(settings.vector_store_dir)

    logger.info(f"开始导入文档: {docs_dir}")

    # 1. 加载
    documents = load_all_documents(docs_dir)
    if not documents:
        logger.warning("没有可导入的文档")
        return 0

    # 2. 切分
    chunks = split_documents(documents)

    # 3. 向量化
    build_vector_store(chunks, vector_dir, overwrite=overwrite)

    source_files = len(set(d.metadata.get("source", "?") for d in documents))
    logger.info(f"导入完成: {source_files} 个文件, {len(chunks)} 个向量")
    return len(chunks)
