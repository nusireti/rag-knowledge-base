"""
RAG 知识库 - 高级版 Web 界面
支持：流式输出/多轮对话/文档管理/暗色主题
"""

import os
import json
import streamlit as st

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

st.set_page_config(page_title="RAG 智能知识库", page_icon="🧠", layout="wide")

from ingest import load_documents, split_documents, get_embedding_model, create_vector_store, clear_embedding_cache
from query import create_qa_chain, clear_cache, ask_stream
from config import DOCUMENTS_DIR, VECTOR_STORE_DIR, EMBEDDING_PROVIDER, LLM_PROVIDER, OLLAMA_MODEL, OPENAI_LLM_MODEL, RETRIEVAL_K

# ===================== 自定义 CSS =====================
st.markdown("""
<style>
    /* 全局字体与背景 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%);
    }
    /* 顶部标题栏 */
    .header {
        background: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(108,92,231,0.3);
    }
    .header h1 {
        color: white;
        font-weight: 700;
        font-size: 1.8rem;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .header p {
        color: rgba(255,255,255,0.85);
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }
    /* 状态徽章 */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .badge-online { background: rgba(0,200,83,0.15); color: #00C853; border: 1px solid rgba(0,200,83,0.3); }
    .badge-offline { background: rgba(255,152,0,0.15); color: #FF9800; border: 1px solid rgba(255,152,0,0.3); }
    /* 统计卡片 */
    .stat-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .stat-card .num {
        font-size: 1.6rem;
        font-weight: 700;
        color: #a29bfe;
    }
    .stat-card .label {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.5);
        margin-top: 2px;
    }
    /* 聊天消息 */
    .chat-user {
        background: linear-gradient(135deg, #6C5CE7 0%, #5B4BD8 100%);
        color: white;
        padding: 0.8rem 1.2rem;
        border-radius: 18px 18px 4px 18px;
        max-width: 80%;
        margin-left: auto;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(108,92,231,0.2);
    }
    .chat-assistant {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 0.8rem 1.2rem;
        border-radius: 18px 18px 18px 4px;
        max-width: 92%;
        margin-right: auto;
        margin-bottom: 1rem;
        line-height: 1.6;
    }
    /* 来源卡片 */
    .source-card {
        background: rgba(108,92,231,0.08);
        border: 1px solid rgba(108,92,231,0.15);
        border-radius: 10px;
        padding: 0.6rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.8rem;
    }
    .source-card .tag {
        background: rgba(108,92,231,0.2);
        color: #a29bfe;
        padding: 1px 8px;
        border-radius: 10px;
        font-size: 0.7rem;
        margin-right: 8px;
    }
    /* 侧边栏美化 */
    section[data-testid="stSidebar"] {
        background: rgba(15,15,26,0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    section[data-testid="stSidebar"] .sidebar-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: white;
        margin-bottom: 1.5rem;
        padding-bottom: 0.8rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    /* 文件列表 */
    .file-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.4rem 0.6rem;
        background: rgba(255,255,255,0.03);
        border-radius: 8px;
        margin: 0.2rem 0;
        font-size: 0.8rem;
    }
    .file-item .name { color: rgba(255,255,255,0.8); }
    .file-item .size { color: rgba(255,255,255,0.4); font-size: 0.7rem; }
    /* 隐藏 Streamlit 默认水印 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* 滚动条 */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(108,92,231,0.3); border-radius: 3px; }
    /* 按钮 */
    .stButton > button {
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(108,92,231,0.3);
    }
    /* 输入框 */
    div[data-testid="stChatInput"] {
        background: rgba(255,255,255,0.08) !important;
        border-radius: 24px !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
    }
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] input {
        color: #FFFFFF !important;
        font-size: 1rem !important;
        caret-color: #6C5CE7 !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder,
    div[data-testid="stChatInput"] input::placeholder {
        color: rgba(255,255,255,0.5) !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #6C5CE7 !important;
        box-shadow: 0 0 0 3px rgba(108,92,231,0.25) !important;
        background: rgba(255,255,255,0.12) !important;
    }
</style>
""", unsafe_allow_html=True)


# ===================== 初始化状态 =====================
for key in ["messages", "qa_chain", "retriever", "ready", "doc_count", "files_info"]:
    if key not in st.session_state:
        if key == "messages":
            st.session_state[key] = []
        elif key == "files_info":
            st.session_state[key] = []
        else:
            st.session_state[key] = None if key in ("qa_chain", "retriever") else (False if key == "ready" else 0)


def get_file_list():
    """获取 documents/ 下的文件列表"""
    docs_dir = DOCUMENTS_DIR
    if not os.path.exists(docs_dir):
        return []
    files = []
    for f in os.listdir(docs_dir):
        fp = os.path.join(docs_dir, f)
        if os.path.isfile(fp):
            size = os.path.getsize(fp)
            files.append({"name": f, "size": size, "path": fp})
    return sorted(files, key=lambda x: x["name"])


def delete_file(filename):
    """删除文件"""
    fp = os.path.join(DOCUMENTS_DIR, filename)
    if os.path.exists(fp):
        os.remove(fp)
        return True
    return False


def rebuild_knowledge_base():
    """重建知识库"""
    clear_cache()
    clear_embedding_cache()

    documents = load_documents(DOCUMENTS_DIR)
    if not documents:
        st.warning("没有文档，请先上传")
        return False

    chunks = split_documents(documents)
    embedding_model = get_embedding_model()
    create_vector_store(chunks, embedding_model)

    st.session_state.files_info = get_file_list()
    st.session_state.ready = True
    st.session_state.doc_count = len(documents)
    return True


# ===================== 预加载 =====================
if not st.session_state.ready and os.path.exists(VECTOR_STORE_DIR) and any(os.scandir(VECTOR_STORE_DIR)):
    try:
        from query import create_qa_chain
        st.session_state.qa_chain, st.session_state.retriever = create_qa_chain()
        st.session_state.ready = True
        docs = load_documents(DOCUMENTS_DIR)
        st.session_state.doc_count = len(docs) if docs else 0
        st.session_state.files_info = get_file_list()
    except Exception:
        pass


# ===================== 页面布局 =====================

# --- 顶部标题 ---
st.markdown("""
<div class="header">
    <h1>🧠 RAG 智能知识库</h1>
    <p>上传文档，让 AI 基于你的内容回答问题</p>
</div>
""", unsafe_allow_html=True)

# --- 状态栏 ---
ready = st.session_state.ready
badge = '<span class="badge badge-online">● 已就绪</span>' if ready else '<span class="badge badge-offline">● 未加载</span>'
st.markdown(f"""
<div style="display:flex; gap:1rem; margin-bottom:1.5rem; flex-wrap:wrap;">
    <div class="stat-card"><div class="num">{st.session_state.doc_count}</div><div class="label">文档段数</div></div>
    <div class="stat-card"><div class="num">{len(st.session_state.files_info)}</div><div class="label">文件数</div></div>
    <div class="stat-card"><div class="num">{LLM_PROVIDER.upper()}</div><div class="label">LLM 类型</div></div>
    <div style="display:flex;align-items:center;">{badge}</div>
</div>
""", unsafe_allow_html=True)

# --- 侧边栏 ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ 管理面板</div>', unsafe_allow_html=True)

    # 上传文档
    st.markdown("**📤 上传文档**")
    uploaded = st.file_uploader(
        "选择文件",
        type=["pdf", "txt", "md", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded:
        os.makedirs(DOCUMENTS_DIR, exist_ok=True)
        for f in uploaded:
            with open(os.path.join(DOCUMENTS_DIR, f.name), "wb") as fh:
                fh.write(f.getbuffer())
        st.session_state.files_info = get_file_list()
        st.toast(f"已保存 {len(uploaded)} 个文件", icon="✅")

    # 刷新按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 刷新知识库", use_container_width=True, type="primary"):
            with st.spinner("正在处理..."):
                if rebuild_knowledge_base():
                    st.toast("知识库构建完成！", icon="🎉")
                    st.rerun()
    with col2:
        if st.button("💬 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # 文档列表
    st.markdown("---")
    st.markdown("**📂 文档列表**")
    files = st.session_state.files_info
    if not files:
        st.caption("暂无文档")
    else:
        for f in files:
            sz = f["size"]
            sz_str = f"{sz/1024:.1f} KB" if sz > 1024 else f"{sz} B"
            colA, colB = st.columns([4, 1])
            with colA:
                st.markdown(f'<div style="font-size:0.8rem;color:rgba(255,255,255,0.8);">{f["name"]}</div>', unsafe_allow_html=True)
            with colB:
                if st.button("✕", key=f"del_{f['name']}", help=f"删除 {f['name']}"):
                    delete_file(f["name"])
                    st.session_state.files_info = get_file_list()
                    st.rerun()
        st.caption(f"共 {len(files)} 个文件")

    # 设置
    st.markdown("---")
    st.markdown("**⚡ 快捷设置**")
    if st.button("🧹 清空向量库 + 重置", use_container_width=True):
        import shutil
        if os.path.exists(VECTOR_STORE_DIR):
            shutil.rmtree(VECTOR_STORE_DIR)
        clear_cache()
        clear_embedding_cache()
        st.session_state.ready = False
        st.session_state.doc_count = 0
        st.session_state.messages = []
        st.toast("已重置", icon="🧹")
        st.rerun()

    st.caption("RAG v2.0 | 大三 AI 作品")


# ===================== 主对话区 =====================

if not st.session_state.ready:
    st.info("💡 请先在左侧上传文档，然后点击 **「刷新知识库」** 开始使用")
else:
    # 对话历史
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            st.markdown(f'<div class="chat-user">💬 {content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-assistant">🤖 {content}</div>', unsafe_allow_html=True)
            if "sources" in msg and msg["sources"]:
                for s in msg["sources"]:
                    st.markdown(
                        f'<div class="source-card">'
                        f'<span class="tag">📄 {s["source"]}</span>'
                        f'{s["content"]}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # 输入框
    if prompt := st.chat_input("输入你的问题..."):
        # 显示用户消息
        st.markdown(f'<div class="chat-user">💬 {prompt}</div>', unsafe_allow_html=True)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 流式生成回答
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                # 只传最近的对话历史
                history = st.session_state.messages[:-1]

                for chunk in ask_stream(prompt, chat_history=history):
                    full_response += chunk
                    # 检查是否包含来源标记
                    if "__SOURCES__:" in full_response:
                        break
                    placeholder.markdown(f'<div class="chat-assistant">🤖 {full_response}▌</div>', unsafe_allow_html=True)

                # 分离回答和来源
                answer = full_response
                sources_data = []
                if "__SOURCES__:" in answer:
                    parts = answer.split("__SOURCES__:")
                    answer = parts[0]
                    try:
                        sources_data = json.loads(parts[1])
                    except json.JSONDecodeError:
                        sources_data = []

                placeholder.markdown(f'<div class="chat-assistant">🤖 {answer}</div>', unsafe_allow_html=True)

                # 显示来源
                if sources_data:
                    for s in sources_data:
                        st.markdown(
                            f'<div class="source-card">'
                            f'<span class="tag">📄 {s["source"]}</span>'
                            f'{s["content"]}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources_data,
                })

            except Exception as e:
                st.error(f"出错了: {e}")
                st.info("点击左侧「刷新知识库」试试")
