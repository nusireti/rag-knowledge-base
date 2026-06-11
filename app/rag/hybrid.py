"""
混合检索器：向量检索 + BM25 关键词检索 + Rerank 重排序
三种方式互补，大幅提升召回准确率
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import settings
from app.logger import logger


class HybridRetriever:
    """
    混合检索器

    融合三种检索方式：
    1. 向量检索（语义相似度）
    2. BM25 检索（关键词匹配）
    3. Rerank 重排序（Cross-Encoder）

    使用方式：
        retriever = HybridRetriever(vector_dir)
        docs = retriever.invoke("你的问题")
    """

    def __init__(self, vector_dir: str):
        self.vector_dir = vector_dir
        self.vector_store: Optional[Chroma] = None
        self.bm25 = None
        self.bm25_docs: List[Document] = []
        self._bm25_path = Path(vector_dir) / "bm25_index.pkl"

    def _load_vector_store(self) -> Chroma:
        """加载向量存储"""
        if self.vector_store is not None:
            return self.vector_store
        from app.rag.embed import get_embedding_model
        self.vector_store = Chroma(
            persist_directory=self.vector_dir,
            embedding_function=get_embedding_model(),
        )
        return self.vector_store

    def _build_bm25_index(self):
        """构建/加载 BM25 索引"""
        if self.bm25 is not None:
            return

        if self._bm25_path.exists():
            try:
                with open(self._bm25_path, "rb") as f:
                    data = pickle.load(f)
                self.bm25 = data["bm25"]
                self.bm25_docs = data["docs"]
                logger.debug(f"BM25 索引已加载: {len(self.bm25_docs)} 文档")
                return
            except Exception as e:
                logger.warning(f"BM25 索引加载失败，将重建: {e}")

        # 从向量库中获取所有文档构建 BM25 索引
        try:
            vs = self._load_vector_store()
            # Chroma 没有直接的 get_all_docs，通过 collection 获取
            collection = vs._collection
            all_data = collection.get(include=["documents", "metadatas"])
            if all_data and all_data["documents"]:
                BM25Okapi = self._get_bm25()
                if BM25Okapi is None:
                    logger.warning("rank_bm25 未安装，跳过 BM25 索引构建")
                    return
                tokenized = [self._tokenize(doc) for doc in all_data["documents"]]
                self.bm25 = BM25Okapi(tokenized)
                self.bm25_docs = [
                    Document(page_content=doc, metadata=meta or {})
                    for doc, meta in zip(all_data["documents"], all_data["metadatas"] or [{}] * len(all_data["documents"]))
                ]
                # 持久化
                with open(self._bm25_path, "wb") as f:
                    pickle.dump({"bm25": self.bm25, "docs": self.bm25_docs}, f)
                logger.info(f"BM25 索引已构建: {len(self.bm25_docs)} 文档")
        except Exception as e:
            logger.warning(f"BM25 索引构建失败（不影响向量检索）: {e}")

    @staticmethod
    def _get_bm25():
        try:
            from rank_bm25 import BM25Okapi
            return BM25Okapi
        except ImportError:
            return None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """中文 + 英文分词"""
        import re
        # 中文按字切分 + 英文按词切分
        tokens = []
        for word in re.findall(r'[一-鿿]|[a-zA-Z0-9]+', text.lower()):
            if re.match(r'[一-鿿]', word):
                tokens.append(word)
            else:
                tokens.append(word)
        return tokens

    def invoke(
        self,
        query: str,
        k: int = None,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        rerank: bool = True,
    ) -> List[Document]:
        """
        混合检索

        参数:
            query: 查询文本
            k: 返回文档数量（默认使用配置值）
            vector_weight: 向量检索权重 (0-1)
            bm25_weight: BM25 检索权重 (0-1)
            rerank: 是否使用 Rerank 重排序

        返回:
            按相关性排序的文档列表
        """
        if k is None:
            k = settings.RETRIEVAL_K * 2  # 混合检索多取一些

        all_docs: dict[str, Tuple[Document, float]] = {}

        # 1. 向量检索
        try:
            vs = self._load_vector_store()
            retriever = vs.as_retriever(
                search_type=settings.RETRIEVAL_SEARCH_TYPE,
                search_kwargs={"k": k},
            )
            vector_docs = retriever.invoke(query)
            for i, doc in enumerate(vector_docs):
                score = (k - i) / k * vector_weight
                doc_id = doc.page_content[:100]  # 用内容前缀做 id
                if doc_id not in all_docs or score > all_docs[doc_id][1]:
                    all_docs[doc_id] = (doc, score)
        except Exception as e:
            logger.error(f"向量检索失败: {e}")

        # 2. BM25 检索
        try:
            self._build_bm25_index()
            if self.bm25 and self.bm25_docs:
                tokenized_query = self._tokenize(query)
                bm25_scores = self.bm25.get_scores(tokenized_query)
                # 取 top-k
                top_indices = sorted(
                    range(len(bm25_scores)),
                    key=lambda i: bm25_scores[i],
                    reverse=True,
                )[:k]
                for rank, idx in enumerate(top_indices):
                    if bm25_scores[idx] > 0:
                        score = (k - rank) / k * bm25_weight
                        doc = self.bm25_docs[idx]
                        doc_id = doc.page_content[:100]
                        if doc_id not in all_docs or score > all_docs[doc_id][1]:
                            all_docs[doc_id] = (doc, score)
        except Exception as e:
            logger.debug(f"BM25 检索跳过（首次使用需构建索引）: {e}")

        # 按分数排序取 top-k
        sorted_docs = sorted(all_docs.values(), key=lambda x: x[1], reverse=True)

        # 3. Rerank 重排序（可选）
        if rerank and len(sorted_docs) > 1:
            try:
                sorted_docs = self._rerank(query, sorted_docs)
            except Exception as e:
                logger.debug(f"Rerank 跳过: {e}")

        result = [doc for doc, _ in sorted_docs[:settings.RETRIEVAL_K]]
        logger.info(f"混合检索: 查询='{query[:30]}...' -> {len(result)} 结果")
        return result

    def _rerank(
        self,
        query: str,
        docs: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """
        Cross-Encoder Rerank 重排序

        使用交叉编码器对检索结果重新排序，提升相关性
        """
        try:
            from sentence_transformers import CrossEncoder

            # 使用轻量级中文 rerank 模型
            model = CrossEncoder("BAAI/bge-reranker-base", device="cpu")
            pairs = [(query, doc.page_content[:512]) for doc, _ in docs]
            scores = model.predict(pairs)

            # 按新分数排序
            scored = [(docs[i][0], float(scores[i])) for i in range(len(docs))]
            scored.sort(key=lambda x: x[1], reverse=True)
            logger.debug(f"Rerank 完成: {len(scored)} 文档重排序")
            return scored
        except ImportError:
            raise RuntimeError("需要安装 sentence-transformers")
        except Exception as e:
            logger.warning(f"Rerank 失败: {e}")
            return docs


def get_hybrid_retriever(vector_dir: str = None) -> HybridRetriever:
    """获取混合检索器实例"""
    if vector_dir is None:
        vector_dir = str(settings.vector_store_dir)
    return HybridRetriever(vector_dir)
