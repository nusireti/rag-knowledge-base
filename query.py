"""
检索 + 生成（旧版 - 保持向后兼容）
新版代码请使用 app/rag/engine.py
"""

import os
import re
from typing import List, Optional, Generator
from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
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

# ============ 全局缓存 ============
_embedding_model_cache = None
_vector_store_cache = None
_llm_cache = None
_llm_stream_cache = None


def get_embedding_model():
    global _embedding_model_cache
    if _embedding_model_cache is not None:
        return _embedding_model_cache
    if EMBEDDING_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("未设置 OPENAI_API_KEY")
        _embedding_model_cache = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY)
    else:
        os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
        _embedding_model_cache = HuggingFaceEmbeddings(
            model_name=LOCAL_EMBEDDING_MODEL,
            model_kwargs={"device": "cpu", "local_files_only": True},
            encode_kwargs={"normalize_embeddings": True})
    return _embedding_model_cache


def get_llm(streaming=False):
    global _llm_cache, _llm_stream_cache
    if streaming:
        if _llm_stream_cache is not None:
            return _llm_stream_cache
    else:
        if _llm_cache is not None:
            return _llm_cache

    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("未设置 OPENAI_API_KEY")
        llm = ChatOpenAI(model=OPENAI_LLM_MODEL, temperature=0.1,
                         streaming=streaming, openai_api_key=OPENAI_API_KEY)
    else:
        llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL,
                         temperature=0.1, num_predict=2048, num_ctx=4096)

    if streaming:
        _llm_stream_cache = llm
    else:
        _llm_cache = llm
    return llm


def load_vector_store(vector_dir: str = None):
    global _vector_store_cache
    if vector_dir is None:
        vector_dir = VECTOR_STORE_DIR
    if _vector_store_cache is not None:
        return _vector_store_cache
    _vector_store_cache = Chroma(
        persist_directory=vector_dir,
        embedding_function=get_embedding_model())
    return _vector_store_cache


def refresh_vector_store(vector_dir: str = None):
    global _vector_store_cache, _embedding_model_cache
    _vector_store_cache = None
    _embedding_model_cache = None
    return load_vector_store(vector_dir)


def clear_cache():
    global _embedding_model_cache, _vector_store_cache, _llm_cache, _llm_stream_cache
    _embedding_model_cache = None
    _vector_store_cache = None
    _llm_cache = None
    _llm_stream_cache = None


def format_docs(docs: List[Document]) -> str:
    texts = []
    for i, doc in enumerate(docs, 1):
        src = doc.metadata.get("source", "未知来源")
        texts.append(f"[来源 {i}: {src}]\n{doc.page_content}")
    return "\n\n---\n\n".join(texts)


def retrieve_docs(question: str, vector_dir: str = None) -> List[Document]:
    vs = load_vector_store(vector_dir)
    retriever = vs.as_retriever(
        search_type=RETRIEVAL_SEARCH_TYPE,
        search_kwargs={"k": RETRIEVAL_K})
    return retriever.invoke(question)


def _build_messages(question: str, context: str, chat_history: List[dict] = None):
    """
    构建带正确角色分工的消息列表。
    系统指令作为 SystemMessage，对话历史 + 当前问题作为 HumanMessage。
    这才是 LLM 能正确理解的关键。
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # 对话历史
    if chat_history and len(chat_history) > 2:
        recent = chat_history[-8:] if len(chat_history) > 8 else chat_history
        for msg in recent:
            if msg["role"] == "user":
                # 如果历史消息中有来源信息，附加到消息中
                content = msg["content"]
                if "sources" in msg and msg["sources"]:
                    src_text = "\n".join(
                        f"  [{s.get('source','文档')}] {s.get('content','')[:100]}"
                        for s in msg["sources"][:2])
                    content += f"\n(参考来源:\n{src_text})"
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=msg["content"]))

    # 当前问题 + 文档上下文
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


def clean_deepseek_output(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = cleaned.strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned


def ask(question: str, vector_dir: str = None) -> dict:
    """问答（非流式，用于终端模式）"""
    source_docs = retrieve_docs(question, vector_dir)
    context = format_docs(source_docs)
    messages = _build_messages(question, context)

    llm = get_llm(streaming=False)
    raw_answer = llm.invoke(messages).content
    answer = clean_deepseek_output(raw_answer)

    return {"question": question, "answer": answer, "source_documents": source_docs}


def ask_stream(question: str, chat_history: List[dict] = None, vector_dir: str = None) -> Generator[str, None, None]:
    """
    流式问答（用于 Web 界面）
    使用正确的 SystemMessage/HumanMessage 角色分工
    """
    source_docs = retrieve_docs(question, vector_dir)
    context = format_docs(source_docs)
    messages = _build_messages(question, context, chat_history)

    # 流式调用，实时过滤 <think> 标签
    llm = get_llm(streaming=True)
    in_think = False
    think_buffer = ""

    for chunk in llm.stream(messages):
        content = chunk.content
        if not content:
            continue

        if in_think:
            think_buffer += content
            end_idx = think_buffer.find("</think>")
            if end_idx >= 0:
                remaining = think_buffer[end_idx + 8:]
                if remaining.strip():
                    remaining = re.sub(r'^\s*\n\s*', '\n', remaining)
                    yield remaining
                think_buffer = ""
                in_think = False
            continue

        start_idx = content.find("<think>")
        if start_idx >= 0:
            before = content[:start_idx]
            if before.strip():
                yield before
            in_think = True
            think_buffer = content[start_idx + 7:]
            end_idx = think_buffer.find("</think>")
            if end_idx >= 0:
                remaining = think_buffer[end_idx + 8:]
                if remaining.strip():
                    yield remaining
                think_buffer = ""
                in_think = False
            continue

        yield content

    # 来源信息
    sources_data = []
    for doc in source_docs[:4]:
        sources_data.append({
            "source": doc.metadata.get("source", "未知"),
            "content": doc.page_content[:200],
        })
    import json
    yield f"\n\n__SOURCES__:{json.dumps(sources_data, ensure_ascii=False)}"


def create_qa_chain(vector_dir: str = None):
    """创建 LCEL 问答链（兼容旧接口）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "以下是与问题相关的文档内容：\n\n{context}\n\n---\n\n问题：{question}"),
    ])
    vs = load_vector_store(vector_dir)
    retriever = vs.as_retriever(
        search_type=RETRIEVAL_SEARCH_TYPE,
        search_kwargs={"k": RETRIEVAL_K})
    llm = get_llm(streaming=False)
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt | llm | StrOutputParser())
    return chain, retriever


def interactive_mode():
    """终端交互模式"""
    print("=" * 50)
    print("RAG 知识库问答系统")
    print("=" * 50)
    load_vector_store()
    print("就绪！输入 'exit' 退出\n")
    history = []
    while True:
        q = input("\n问题: ").strip()
        if q.lower() in ("exit", "quit", "q"):
            break
        if not q:
            continue
        result = ask(q)
        print(f"\n{result['answer']}")
        history.extend([
            {"role": "user", "content": q},
            {"role": "assistant", "content": result['answer']},
        ])


if __name__ == "__main__":
    interactive_mode()
