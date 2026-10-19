"""
RAG 问答引擎
检索 -> 构建提示 -> LLM 生成
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Generator, List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings
from app.logger import logger
from app.rag.embed import get_embedding_model


def _get_provider() -> str:
    """获取当前 LLM 提供商（优先级：环境变量 > 配置文件）"""
    return os.environ.get("LLM_PROVIDER", settings.LLM_PROVIDER)


def _get_ollama_model() -> str:
    """
    获取当前 Ollama 模型名（优先级：环境变量 > 配置文件）

    settings.OLLAMA_MODEL 是 pydantic 字段，进程启动那一刻就固化了。
    界面上"切换模型"只改环境变量，所以这里必须每次动态读，
    否则切换是空操作 —— 界面显示变了、实际答话的还是旧模型。
    """
    return os.environ.get("OLLAMA_MODEL", settings.OLLAMA_MODEL)


def _get_ollama_base_url() -> str:
    """获取当前 Ollama 服务地址（支持运行时切换）"""
    return os.environ.get("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)


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

    provider = _get_provider()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openai 但未设置 OPENAI_API_KEY")
        llm = ChatOpenAI(
            model=settings.OPENAI_LLM_MODEL,
            streaming=streaming,
            openai_api_key=settings.OPENAI_API_KEY,
            **common_kwargs,
        )

    elif provider == "dashscope":
        if not settings.DASHSCOPE_API_KEY:
            raise RuntimeError("LLM_PROVIDER=dashscope 但未设置 DASHSCOPE_API_KEY")
        llm = ChatOpenAI(
            model=settings.DASHSCOPE_LLM_MODEL,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            openai_api_key=settings.DASHSCOPE_API_KEY,
            streaming=streaming,
            **common_kwargs,
        )

    elif provider == "deepseek":
        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("LLM_PROVIDER=deepseek 但未设置 DEEPSEEK_API_KEY")
        llm = ChatOpenAI(
            model=settings.DEEPSEEK_LLM_MODEL,
            base_url="https://api.deepseek.com",
            openai_api_key=settings.DEEPSEEK_API_KEY,
            streaming=streaming,
            **common_kwargs,
        )

    else:
        # 自动检测 GPU
        num_gpu = _detect_gpu()
        llm_kwargs = {
            "model": _get_ollama_model(),
            "base_url": _get_ollama_base_url(),
            "num_predict": settings.LLM_MAX_TOKENS,
            "num_ctx": settings.LLM_CONTEXT_WINDOW,
            **common_kwargs,
        }
        if num_gpu > 0:
            # num_gpu=-1 让 Ollama 尽可能把模型层加载进 GPU（RTX4060 8G 显存足够）
            llm_kwargs["num_gpu"] = -1
            logger.info(f"GPU 加速已启用 ({num_gpu} 个 GPU)")

        try:
            from langchain_ollama import ChatOllama
            llm = ChatOllama(**llm_kwargs)
        except ImportError:
            logger.error("langchain-ollama 未安装，无法使用本地模型")
            raise RuntimeError("使用 LLM_PROVIDER=local 需要安装 langchain-ollama")

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

# 按向量库目录缓存，key = 规范化后的绝对路径。
# 早先这里是单个全局变量，忽略 vector_dir —— 一旦切换知识库就会串味：
# 混合检索失败降级到纯向量检索时，会拿到上一个知识库的向量库，
# 于是答出另一个库的内容，且是静默的、偶发的。
_vector_store_cache: dict = {}


def get_vector_store(vector_dir: Optional[str] = None) -> Chroma:
    """获取向量存储实例（按目录缓存，不同知识库互不影响）"""
    vector_dir = str(Path(vector_dir or settings.vector_store_dir).resolve())
    key = vector_dir

    cached = _vector_store_cache.get(key)
    if cached is not None:
        return cached

    store = Chroma(
        persist_directory=vector_dir,
        embedding_function=get_embedding_model(),
    )
    _vector_store_cache[key] = store
    return store


def clear_vector_store_cache(vector_dir: Optional[str] = None):
    """
    清空向量库缓存。

    vector_dir 为 None 时清空全部；否则只清指定目录。
    重建索引后必须调用，否则缓存里还指着已被删除的旧目录。
    """
    if vector_dir is None:
        _vector_store_cache.clear()
        return
    _vector_store_cache.pop(str(Path(vector_dir).resolve()), None)


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
    t0 = time.perf_counter()

    if use_hybrid:
        try:
            from app.rag.hybrid import get_hybrid_retriever
            retriever = get_hybrid_retriever(vector_dir)
            docs = retriever.invoke(question)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info(
                f"[RAG] retrieve mode=hybrid chunks={len(docs)} elapsed={elapsed:.0f}ms"
            )
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
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            f"[RAG] retrieve mode=vector chunks={len(docs)} elapsed={elapsed:.0f}ms"
        )
        return docs
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        logger.error(f"检索失败: {e} (elapsed={elapsed:.0f}ms)")
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
    t0 = time.perf_counter()
    sources = retrieve_docs(question, vector_dir)
    context = format_docs(sources)
    messages = _build_messages(question, context)

    llm = get_llm(streaming=False)
    t_llm = time.perf_counter()
    raw = llm.invoke(messages).content
    answer = clean_output(raw)

    logger.info(
        f"[RAG] answer mode=non-stream sources={len(sources)} "
        f"llm={(time.perf_counter() - t_llm) * 1000:.0f}ms "
        f"total={(time.perf_counter() - t0) * 1000:.0f}ms"
    )
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
    t_start = time.perf_counter()
    sources = retrieve_docs(question, vector_dir)
    t_retrieved = time.perf_counter()
    context = format_docs(sources)
    messages = _build_messages(question, context, chat_history)

    llm = get_llm(streaming=True)
    in_think = False
    buffer = ""
    first_token_at = None

    for chunk in llm.stream(messages):
        content = chunk.content
        if not content:
            continue
        if first_token_at is None:
            first_token_at = time.perf_counter()

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

    t_end = time.perf_counter()
    ttft_ms = (first_token_at - t_retrieved) * 1000 if first_token_at else -1
    logger.info(
        f"[RAG] stream sources={len(sources)} "
        f"retrieve={(t_retrieved - t_start) * 1000:.0f}ms "
        f"ttft={ttft_ms:.0f}ms "
        f"generate={(t_end - t_retrieved) * 1000:.0f}ms "
        f"total={(t_end - t_start) * 1000:.0f}ms"
    )

    # 来源信息
    sources_data = [
        {"source": d.metadata.get("source", "未知"), "content": d.page_content[:200]}
        for d in sources[:4]
    ]
    yield f"\n\n__SOURCES__:{json.dumps(sources_data, ensure_ascii=False)}"

# ---- 模型预热 ----
#
# 早先这里是"import 即起线程"的副作用：只要 import 本模块就会联网加载模型，
# 导致单元测试、脚本工具、CI 都被迫等它，而且失败信息藏在后台线程里。
# 改为显式调用，由应用入口（ui.py）在启动时触发。
_warmup_started = False


def start_warmup():
    """启动后台模型预热（重复调用无副作用）"""
    global _warmup_started
    if _warmup_started:
        return
    _warmup_started = True
    import threading
    threading.Thread(target=_warmup_llm, daemon=True).start()
