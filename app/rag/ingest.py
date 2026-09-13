"""
文档导入管道
加载 -> 切分 -> 向量化 -> 存储
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Set

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import settings
from app.logger import logger
from app.rag.loaders import load_document


def _invalidate_caches(vector_dir: str):
    """
    索引内容变化后，让所有相关缓存失效。

    三处缓存都指向"重建前的旧数据"，不清就会拿到已删文档的内容：
    - bm25_index.pkl（磁盘）：下次查询自动从向量库重建
    - engine 的向量库实例缓存（内存）
    - hybrid 的检索器实例缓存（内存，内含 Chroma 句柄和 BM25 索引）
    """
    from app.rag.engine import clear_vector_store_cache
    from app.rag.hybrid import clear_hybrid_cache

    pkl = Path(vector_dir) / "bm25_index.pkl"
    if pkl.exists():
        pkl.unlink()

    clear_vector_store_cache(vector_dir)
    clear_hybrid_cache(vector_dir)


def remove_document_chunks(vector_dir: str, filename: str) -> int:
    """
    从向量库中删除某个文档的全部切块（增量删除，不重建整个库）

    参数:
        vector_dir: 向量库目录
        filename: 文档的 source 元数据（存的是文件名，见 loaders.load_document）

    返回:
        删除的切块数；-1 表示出错。

    注意:
        返回 0 有两种可能：该文件本来就没进索引，或者索引是旧格式
        （source 存的是绝对路径，早先版本的行为）匹配不上。
        两种情况调用方都应回退到全量重建，不要当成"删干净了"。
    """
    from app.rag.engine import get_vector_store

    try:
        store = get_vector_store(vector_dir)
        existing = store._collection.get(where={"source": filename}, include=[])
        ids = existing.get("ids") or []
        if ids:
            store._collection.delete(ids=ids)

        _invalidate_caches(vector_dir)
        logger.info(f"已从索引中删除 {len(ids)} 个切块: {filename}")
        return len(ids)
    except Exception as e:
        logger.warning(f"增量删除失败（可回退到全量重建）: {e}")
        return -1


def clear_index(vector_dir: str):
    """
    清空向量库内容（保留目录本身）

    知识库里已经没有任何文档时必须调用：不清的话，删掉最后一个文档后，
    库里还留着它的切块，问什么都能答出来 —— 比"删不干净"更离谱。

    刻意不走 shutil.rmtree 删目录：Windows 上只要进程里还持有 Chroma
    客户端句柄，删目录就 PermissionError（该句柄由 chromadb 内部系统缓存
    持有，clear_system_cache + gc 都释放不掉）。所以走集合 API 清空内容。
    """
    from app.rag.engine import get_vector_store

    _invalidate_caches(vector_dir)
    store = get_vector_store(vector_dir)
    store.reset_collection()
    _invalidate_caches(vector_dir)
    logger.info(f"向量库已清空: {vector_dir}")


def index_single_file(vector_dir: str, file_path: str) -> int:
    """
    把单个文件增量加入向量库（不重建整个库）

    参数:
        vector_dir: 向量库目录
        file_path: 已落盘的文档路径

    返回:
        新增的切块数；加载失败或无内容返回 -1
    """
    from app.rag.engine import get_vector_store

    filename = Path(file_path).name
    try:
        documents = load_document(file_path)
        if not documents:
            logger.warning(f"文件无可索引内容: {filename}")
            return -1

        chunks = split_documents(documents)
        store = get_vector_store(vector_dir)
        store.add_documents(chunks)
        _invalidate_caches(vector_dir)
        logger.info(f"增量索引完成 {filename}: {len(chunks)} 个切块")
        return len(chunks)
    except Exception as e:
        logger.warning(f"增量索引失败 {filename}: {e}")
        return -1


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
    from app.rag.engine import get_vector_store

    if overwrite:
        clear_index(vector_dir)

    vector_store = get_vector_store(vector_dir)
    vector_store.add_documents(chunks)
    _invalidate_caches(vector_dir)
    logger.info(f"向量库写入完成: {len(chunks)} 个向量")
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
