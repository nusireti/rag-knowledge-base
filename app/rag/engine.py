"""
RAG 问答引擎
检索 -> 构建提示 -> LLM 生成
"""

from __future__ import annotations

import json
import re
from typing import Generator, List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.config import settings
from app.logger import logger
from app.rag.embed import get_embedding_model

# ---- LLM 工厂 ----

_llm_cache = None
_llm_stream_cache = None


def _warmup_llm():
    """模型预热：发送一次空请求让 GPU 加载模型"""
    global _llm_cache
    try:
        if _llm_cache is None:
            llm = get_llm(streaming=False)
            from langchain_core.messages import HumanMessage
            llm.invoke([HumanMessage(content="1")])
            logger.info("LLM 模型预热完成")
    except Exception as e:
        logger.warning(f"模型预热失败（不影响使用）: {e}")


def get_llm(streaming: bool = False) -> BaseChatModel:
    """
    获取 LLM 实例（全局缓存）

    自动检测 NVIDIA GPU 并启用加速
    """
    global _llm_cache, _llm_stream_cache

    cache = _llm_stream_cache if streaming else _llm_cache
    if cache is not None:
        return cache

    common_kwargs = {
        "temperature": settings.LLM_TEMPERATURE,
    }

    if settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openai 但未设置 OPENAI_API_KEY")
        llm = ChatOpenAI(
            model=settings.OPENAI_LLM_MODEL,
            streaming=streaming,
            openai_api_key=settings.OPENAI_API_KEY,
            **common_kwargs,
        )
    else:
        # 自动检测 GPU
        num_gpu = _detect_gpu()
        llm_kwargs = {
            "model": settings.OLLAMA_MODEL,
            "base_url": settings.OLLAMA_BASE_URL,
            "num_predict": settings.LLM_MAX_TOKENS,
            "num_ctx": settings.LLM_CONTEXT_WINDOW,
            **common_kwargs,
        }
        if num_gpu > 0:
            llm_kwargs["num_gpu"] = num_gpu
            logger.info(f"GPU 加速已启用 ({num_gpu} 个 GPU)")

        llm = ChatOllama(**llm_kwargs)

    if streaming:
        _llm_stream_cache = llm
    else:
        _llm_cache = llm

    return llm


def _detect_gpu() -> int:
    """检测可用的 NVIDIA GPU 数量"""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            gpu_count = len([l for l in result.stdout.strip().split("\n") if l.strip()])
            return gpu_count
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return 0


def clear_llm_cache():
    global _llm_cache, _llm_stream_cache
    _llm_cache = None
    _llm_stream_cache = None


# ---- 提示词 ----

SYSTEM_PROMPT = """你是一个知识库问答助手，严格基于提供的文档内容回答。

## 铁律
1. 只基于上面"相关内容"中的文字回答，绝不编造
2. 直接回答，不要任何铺垫、过渡、客套话
3. 不要解释你在做什么，不要分析问题，不要自我纠正
4. 如果相关内容里没有答案，只回复"文档中没有相关信息"，不要补充

## 回答格式
- 总结/复述：直接列出要点，每行一个
- 具体问题：直接给答案
- 多条信息：用 - 分点列出

## 禁止
- ❌ "好的"、"首先"、"值得注意的是"、"总的来说" 等废话
- ❌ 复述问题
- ❌ 评价文档内容好坏
- ❌ 自己编造文档没有的信息"""


def _build_messages(
    question: str,
    context: str,
    chat_history: Optional[List[dict]] = None,
) -> list:
    """
    构建消息列表，使用正确的 SystemMessage/HumanMessage 角色分工
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # 对话历史
    if chat_history and len(chat_history) > 2:
        for msg in chat_history[-8:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                content = msg.get("content", "")
                messages.append(AIMessage(content=content))

    # 当前问题 + 上下文
    if context.strip():
        user_content = f"""以下是与问题相关的文档内容：

{context}

---

请基于上面提供的文档内容回答用户的问题。
如果文档内容与问题无关或没有足够信息，请如实说"文档中没有相关信息"。

问题: {question}"""
    else:
        user_content = f"""没有检索到相关的文档内容。

问题: {question}"""

    messages.append(HumanMessage(content=user_content))
    return messages


# ---- 向量存储 ----

_vector_store_cache = None


def get_vector_store(vector_dir: Optional[str] = None) -> Chroma:
    """获取向量存储实例（全局缓存）"""
    global _vector_store_cache
    vector_dir = vector_dir or str(settings.vector_store_dir)

    if _vector_store_cache is not None:
        return _vector_store_cache

    _vector_store_cache = Chroma(
        persist_directory=vector_dir,
        embedding_function=get_embedding_model(),
    )
    return _vector_store_cache


def clear_vector_store_cache():
    global _vector_store_cache
    _vector_store_cache = None


# ---- 检索 ----

def format_docs(docs: List[Document]) -> str:
    """将文档列表格式化为可读文本"""
    texts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "未知来源")
        texts.append(f"[来源 {i}: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(texts)


def retrieve_docs(
    question: str,
    vector_dir: Optional[str] = None,
    use_hybrid: bool = True,
) -> List[Document]:
    """
    检索相关文档（支持混合检索）

    参数:
        question: 查询文本
        vector_dir: 向量库路径
        use_hybrid: 是否使用 BM25+向量混合检索
    """
    if use_hybrid:
        try:
            from app.rag.hybrid import get_hybrid_retriever
            retriever = get_hybrid_retriever(vector_dir)
            docs = retriever.invoke(question)
            logger.debug(f"混合检索到 {len(docs)} 个文档块")
            return docs
        except Exception as e:
            logger.warning(f"混合检索失败，降级到纯向量检索: {e}")

    # 纯向量检索（兜底）
    try:
        vs = get_vector_store(vector_dir)
        retriever = vs.as_retriever(
            search_type=settings.RETRIEVAL_SEARCH_TYPE,
            search_kwargs={"k": settings.RETRIEVAL_K},
        )
        docs = retriever.invoke(question)
        logger.debug(f"向量检索到 {len(docs)} 个文档块")
        return docs
    except Exception as e:
        logger.error(f"检索失败: {e}")
        return []


# ---- 问答 ----

def clean_output(text: str) -> str:
    """清理模型输出中的思考标签等"""
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = cleaned.strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned


def ask(question: str, vector_dir: Optional[str] = None) -> dict:
    """
    非流式问答

    返回:
        {"answer": str, "source_documents": List[Document]}
    """
    sources = retrieve_docs(question, vector_dir)
    context = format_docs(sources)
    messages = _build_messages(question, context)

    llm = get_llm(streaming=False)
    raw = llm.invoke(messages).content
    answer = clean_output(raw)

    return {"answer": answer, "source_documents": sources}


def ask_stream(
    question: str,
    chat_history: Optional[List[dict]] = None,
    vector_dir: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    流式问答
    实时过滤 think 标签，末尾附加来源信息
    """
    sources = retrieve_docs(question, vector_dir)
    context = format_docs(sources)
    messages = _build_messages(question, context, chat_history)

    llm = get_llm(streaming=True)
    in_think = False
    buffer = ""

    for chunk in llm.stream(messages):
        content = chunk.content
        if not content:
            continue

        if in_think:
            buffer += content
            end = buffer.find("</think>")
            if end >= 0:
                rest = buffer[end + 8:]
                if rest.strip():
                    yield re.sub(r'^\s*\n\s*', '\n', rest)
                buffer = ""
                in_think = False
            continue

        start = content.find("<think>")
        if start >= 0:
            before = content[:start]
            if before.strip():
                yield before
            in_think = True
            buffer = content[start + 7:]
            end = buffer.find("</think>")
            if end >= 0:
                rest = buffer[end + 8:]
                if rest.strip():
                    yield re.sub(r'^\s*\n\s*', '\n', rest)
                buffer = ""
                in_think = False
            continue

        yield content

    # 来源信息
    sources_data = [
        {"source": d.metadata.get("source", "未知"), "content": d.page_content[:200]}
        for d in sources[:4]
    ]
    yield f"\n\n__SOURCES__:{json.dumps(sources_data, ensure_ascii=False)}"

# 后台预热模型
import threading
_t = threading.Thread(target=_warmup_llm, daemon=True)
_t.start()
