"""
检索 + 生成
根据用户问题，从知识库检索相关内容并生成回答

优化:
  - embedding 模型全局缓存（只加载一次）
  - 流式输出支持
  - 多轮对话记忆
"""

import os
from typing import List, Optional, Generator
from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_chroma import Chroma

from config import (
    VECTOR_STORE_DIR,
    EMBEDDING_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENAI_LLM_MODEL,
    RETRIEVAL_K,
    RETRIEVAL_SEARCH_TYPE,
    SYSTEM_PROMPT,
)

# ============ 全局缓存（只加载一次） ============
_embedding_model_cache = None
_vector_store_cache = None
_llm_cache = None
_llm_stream_cache = None


def get_embedding_model():
    """获取 Embedding 模型（全局缓存）"""
    global _embedding_model_cache
    if _embedding_model_cache is not None:
        return _embedding_model_cache

    if EMBEDDING_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("使用 OpenAI Embedding 但未设置 OPENAI_API_KEY")
        _embedding_model_cache = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY,
        )
    else:
        os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
        _embedding_model_cache = HuggingFaceEmbeddings(
            model_name=LOCAL_EMBEDDING_MODEL,
            model_kwargs={
                "device": "cpu",
                "local_files_only": True,
            },
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model_cache


def get_llm(streaming=False):
    """
    获取 LLM 模型
    streaming=True 时返回流式版本（用于 Web 界面）
    """
    global _llm_cache, _llm_stream_cache

    if streaming:
        if _llm_stream_cache is not None:
            return _llm_stream_cache
    else:
        if _llm_cache is not None:
            return _llm_cache

    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("使用 OpenAI LLM 但未设置 OPENAI_API_KEY")
        llm = ChatOpenAI(
            model=OPENAI_LLM_MODEL,
            temperature=0.3,
            streaming=streaming,
            openai_api_key=OPENAI_API_KEY,
        )
    else:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
            num_predict=2048,
            num_ctx=4096,
        )

    if streaming:
        _llm_stream_cache = llm
    else:
        _llm_cache = llm
    return llm


def load_vector_store(vector_dir: str = None):
    """
    加载已有的向量数据库（全局缓存）

    参数:
        vector_dir: 向量数据库目录（默认使用 config.VECTOR_STORE_DIR）
    """
    global _vector_store_cache
    if vector_dir is None:
        vector_dir = VECTOR_STORE_DIR

    if _vector_store_cache is not None:
        return _vector_store_cache

    embedding_model = get_embedding_model()
    _vector_store_cache = Chroma(
        persist_directory=vector_dir,
        embedding_function=embedding_model,
    )
    return _vector_store_cache


def refresh_vector_store(vector_dir: str = None):
    """刷新向量数据库缓存"""
    global _vector_store_cache, _embedding_model_cache
    _vector_store_cache = None
    _embedding_model_cache = None
    return load_vector_store(vector_dir)


def create_qa_chain(vector_dir: str = None):
    """
    创建问答链（兼容旧接口）
    参数:
        vector_dir: 向量数据库目录（默认使用 config.VECTOR_STORE_DIR）
    返回: (chain, retriever)
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough

    vector_store = load_vector_store(vector_dir)
    retriever = vector_store.as_retriever(
        search_type=RETRIEVAL_SEARCH_TYPE,
        search_kwargs={"k": RETRIEVAL_K},
    )
    llm = get_llm(streaming=False)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "以下是与问题相关的文档内容：\n\n{context}\n\n---\n\n问题：{question}"),
    ])

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever


def clear_cache():
    """清空所有缓存"""
    global _embedding_model_cache, _vector_store_cache, _llm_cache, _llm_stream_cache
    _embedding_model_cache = None
    _vector_store_cache = None
    _llm_cache = None
    _llm_stream_cache = None


def format_docs(docs: List[Document]) -> str:
    """把检索到的文档拼接成上下文"""
    texts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "未知来源")
        texts.append(f"[来源 {i}: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(texts)


def retrieve_docs(question: str, vector_dir: str = None) -> List[Document]:
    """只检索文档（不生成回答）"""
    vector_store = load_vector_store(vector_dir)
    retriever = vector_store.as_retriever(
        search_type=RETRIEVAL_SEARCH_TYPE,
        search_kwargs={"k": RETRIEVAL_K},
    )
    return retriever.invoke(question)


def build_prompt_with_history(question: str, context: str, chat_history: List[dict] = None) -> str:
    """
    构建包含对话历史的提示词
    chat_history: [{"role": "user"/"assistant", "content": "..."}]
    """
    history_str = ""
    if chat_history and len(chat_history) > 2:
        # 只保留最近 4 轮对话（避免太长）
        recent = chat_history[-8:] if len(chat_history) > 8 else chat_history
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "AI"
            history_str += f"{role}: {msg['content']}\n"

    parts = [SYSTEM_PROMPT]

    if history_str:
        parts.append(f"以下是对话历史：\n{history_str}")

    parts.append(f"以下是与问题相关的文档内容：\n{context}\n---\n问题：{question}")

    return "\n\n".join(parts)


def ask(question: str, vector_dir: str = None) -> dict:
    """
    问答（非流式，用于终端模式）
    返回: {"question", "answer", "source_documents"}
    """
    source_docs = retrieve_docs(question, vector_dir)
    context = format_docs(source_docs)

    llm = get_llm(streaming=False)
    user_prompt = build_prompt_with_history(question, context)
    answer = llm.invoke(user_prompt).content

    return {
        "question": question,
        "answer": answer,
        "source_documents": source_docs,
    }


def ask_stream(question: str, chat_history: List[dict] = None, vector_dir: str = None) -> Generator[str, None, None]:
    """
    流式问答（用于 Web 界面）
    先检索文档，再流式输出回答

    参数:
        question: 问题
        chat_history: 对话历史
        vector_dir: 向量数据库目录（默认使用 config.VECTOR_STORE_DIR）
    """
    # 检索文档
    source_docs = retrieve_docs(question, vector_dir)
    context = format_docs(source_docs)

    # 构建提示词
    user_prompt = build_prompt_with_history(question, context, chat_history)

    # 流式调用 LLM
    llm = get_llm(streaming=True)
    for chunk in llm.stream(user_prompt):
        yield chunk.content

    # 把来源信息作为最后一个特殊 chunk 返回
    # 格式: __SOURCES__: json_string
    sources_data = []
    for doc in source_docs[:4]:
        sources_data.append({
            "source": doc.metadata.get("source", "未知"),
            "content": doc.page_content[:200],
        })
    import json
    yield f"\n\n__SOURCES__:{json.dumps(sources_data, ensure_ascii=False)}"


def interactive_mode():
    """终端交互模式"""
    print("=" * 50)
    print("RAG 知识库问答系统")
    print("=" * 50)
    print(f"  模型: {OLLAMA_MODEL}")
    print(f"  输入 'exit' 退出")
    print("=" * 50)

    # 预加载
    print("\n加载模型中...")
    load_vector_store()
    print("就绪！\n")

    chat_history = []

    while True:
        question = input("\n请输入问题: ").strip()
        if question.lower() in ("exit", "quit", "q"):
            print("再见！")
            break
        if not question:
            continue

        print("\n思考中...\n")
        try:
            result = ask(question)
            print(f"{result['answer']}")

            chat_history.append({"role": "user", "content": question})
            chat_history.append({"role": "assistant", "content": result['answer']})

            if result["source_documents"]:
                print(f"\n参考来源:")
                for i, doc in enumerate(result["source_documents"][:3], 1):
                    src = doc.metadata.get("source", "未知")
                    preview = doc.page_content[:80].replace("\n", " ")
                    print(f"  {i}. [{src}] {preview}...")
        except Exception as e:
            print(f"出错: {e}")


if __name__ == "__main__":
    interactive_mode()
