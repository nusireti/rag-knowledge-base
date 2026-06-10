"""
RAG 知识库 - 高级版 Web 界面
v2.1: 对话历史持久化 + 导出功能
"""

import os
import json
import streamlit as st
import tempfile

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

st.set_page_config(page_title="RAG 智能知识库", page_icon="🧠", layout="wide")

from ingest import load_documents, split_documents, get_embedding_model, create_vector_store, clear_embedding_cache
from query import create_qa_chain, clear_cache, ask_stream
from config import DOCUMENTS_DIR, VECTOR_STORE_DIR, EMBEDDING_PROVIDER, LLM_PROVIDER, OLLAMA_MODEL, OPENAI_LLM_MODEL
from chat_history import (
    list_conversations, create_conversation, load_conversation,
    save_messages, delete_conversation, export_markdown, export_text,
)

# ===================== CSS =====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%); }
    .header {
        background: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 100%);
        padding: 1.2rem 2rem; border-radius: 16px; margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(108,92,231,0.3);
    }
    .header h1 { color: white; font-weight: 700; font-size: 1.6rem; margin: 0; }
    .header p { color: rgba(255,255,255,0.85); margin: 0.2rem 0 0 0; font-size: 0.9rem; }
    .stat-card {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 0.6rem 1rem; text-align: center;
        backdrop-filter: blur(10px);
    }
    .stat-card .num { font-size: 1.3rem; font-weight: 700; color: #a29bfe; }
    .stat-card .label { font-size: 0.7rem; color: rgba(255,255,255,0.5); }
    .chat-user {
        background: linear-gradient(135deg, #6C5CE7 0%, #5B4BD8 100%);
        color: white; padding: 0.8rem 1.2rem;
        border-radius: 18px 18px 4px 18px; max-width: 80%;
        margin-left: auto; margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(108,92,231,0.2);
    }
    .chat-assistant {
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
        padding: 0.8rem 1.2rem; border-radius: 18px 18px 18px 4px;
        max-width: 92%; margin-right: auto; margin-bottom: 1rem; line-height: 1.6;
    }
    .source-card {
        background: rgba(108,92,231,0.08); border: 1px solid rgba(108,92,231,0.15);
        border-radius: 10px; padding: 0.5rem 0.8rem; margin: 0.3rem 0; font-size: 0.8rem;
    }
    .source-card .tag {
        background: rgba(108,92,231,0.2); color: #a29bfe;
        padding: 1px 8px; border-radius: 10px; font-size: 0.7rem; margin-right: 8px;
    }
    .conv-item {
        padding: 0.5rem 0.6rem; border-radius: 8px; cursor: pointer;
        font-size: 0.85rem; margin: 0.15rem 0;
        background: rgba(255,255,255,0.03);
        transition: all 0.15s;
    }
    .conv-item:hover { background: rgba(108,92,231,0.12); }
    .conv-item.active { background: rgba(108,92,231,0.2); border-left: 3px solid #6C5CE7; }
    section[data-testid="stSidebar"] { background: rgba(15,15,26,0.95) !important; border-right: 1px solid rgba(255,255,255,0.06); }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    div[data-testid="stChatInput"] {
        background: rgba(255,255,255,0.08) !important; border-radius: 24px !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #FFFFFF !important; font-size: 1rem !important; caret-color: #6C5CE7 !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder { color: rgba(255,255,255,0.4) !important; }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #6C5CE7 !important; box-shadow: 0 0 0 3px rgba(108,92,231,0.25) !important;
        background: rgba(255,255,255,0.12) !important;
    }
</style>
""", unsafe_allow_html=True)


# ===================== 初始化状态 =====================
for key in ["messages", "ready", "doc_count", "conv_id", "conv_title"]:
    if key not in st.session_state:
        if key == "messages":
            st.session_state[key] = []
        elif key in ("conv_id", "conv_title"):
            st.session_state[key] = None
        else:
            st.session_state[key] = False if key == "ready" else 0


def get_file_list():
    docs_dir = DOCUMENTS_DIR
    if not os.path.exists(docs_dir):
        return []
    files = []
    for f in sorted(os.listdir(docs_dir)):
        fp = os.path.join(docs_dir, f)
        if os.path.isfile(fp):
            files.append({"name": f, "size": os.path.getsize(fp), "path": fp})
    return files


def delete_file(filename):
    fp = os.path.join(DOCUMENTS_DIR, filename)
    if os.path.exists(fp):
        os.remove(fp)
        return True
    return False


def rebuild_knowledge_base():
    clear_cache()
    clear_embedding_cache()
    documents = load_documents(DOCUMENTS_DIR)
    if not documents:
        st.warning("没有文档")
        return False
    chunks = split_documents(documents)
    embedding_model = get_embedding_model()
    create_vector_store(chunks, embedding_model)
    st.session_state.ready = True
    st.session_state.doc_count = len(documents)
    return True


def switch_conversation(conv_id):
    """切换到指定对话"""
    st.session_state.conv_id = conv_id
    msgs = load_conversation(conv_id)
    st.session_state.messages = msgs if msgs else []
    # 刷新标题显示
    convs = list_conversations()
    for c in convs:
        if c["id"] == conv_id:
            st.session_state.conv_title = c["title"]
            break


def new_conversation():
    """新建对话"""
    conv_id = create_conversation()
    st.session_state.conv_id = conv_id
    st.session_state.conv_title = "新对话"
    st.session_state.messages = []


def save_current_conversation():
    """保存当前对话"""
    if st.session_state.conv_id and st.session_state.messages:
        save_messages(st.session_state.conv_id, st.session_state.messages)


# ===================== 预加载 =====================
if not st.session_state.ready and os.path.exists(VECTOR_STORE_DIR) and any(os.scandir(VECTOR_STORE_DIR)):
    try:
        st.session_state.ready = True
        docs = load_documents(DOCUMENTS_DIR)
        st.session_state.doc_count = len(docs) if docs else 0
    except Exception:
        pass

# 第一次加载时，创建或恢复对话
if st.session_state.conv_id is None:
    convs = list_conversations()
    if convs:
        # 恢复最新的对话
        latest = convs[0]
        switch_conversation(latest["id"])
    else:
        new_conversation()


# ===================== 页面 =====================

# --- 标题 ---
st.markdown("""
<div class="header">
    <h1>🧠 RAG 智能知识库</h1>
    <p>上传文档，让 AI 基于你的内容回答问题 · 对话自动保存</p>
</div>
""", unsafe_allow_html=True)

# --- 状态栏 ---
badge = '<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;font-size:0.75rem;background:rgba(0,200,83,0.15);color:#00C853;border:1px solid rgba(0,200,83,0.3);">● 已就绪</span>' if st.session_state.ready else '<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;font-size:0.75rem;background:rgba(255,152,0,0.15);color:#FF9800;border:1px solid rgba(255,152,0,0.3);">● 未加载</span>'
files = get_file_list()
st.markdown(f"""
<div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;align-items:center;">
    <div class="stat-card"><div class="num">{st.session_state.doc_count}</div><div class="label">文档段</div></div>
    <div class="stat-card"><div class="num">{len(files)}</div><div class="label">文件数</div></div>
    <div class="stat-card"><div class="num">{LLM_PROVIDER.upper()}</div><div class="label">LLM</div></div>
    {badge}
</div>
""", unsafe_allow_html=True)


# ===================== 侧边栏 =====================
with st.sidebar:
    st.markdown("#### ⚙️ 管理面板")

    # ---- 对话管理 ----
    st.markdown("**💬 对话管理**")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        if st.button("＋ 新建对话", use_container_width=True):
            new_conversation()
            st.rerun()
    with col_b:
        if st.button("💾 保存", use_container_width=True):
            save_current_conversation()
            st.toast("已保存", icon="✅")

    # 对话列表
    convs = list_conversations()
    if convs:
        for c in convs:
            active = c["id"] == st.session_state.conv_id
            prefix = "▸ " if active else "  "
            label = f"{prefix}{c['title'][:18]}"
            cols = st.columns([4, 1])
            with cols[0]:
                if st.button(label, key=f"conv_{c['id']}", use_container_width=True):
                    switch_conversation(c["id"])
                    st.rerun()
            with cols[1]:
                if st.button("✕", key=f"del_{c['id']}", help="删除此对话"):
                    delete_conversation(c["id"])
                    if c["id"] == st.session_state.conv_id:
                        remaining = list_conversations()
                        if remaining:
                            switch_conversation(remaining[0]["id"])
                        else:
                            new_conversation()
                    st.rerun()

    # ---- 导出 ----
    if st.session_state.messages:
        st.markdown("**📤 导出当前对话**")
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            md_content = export_markdown(st.session_state.conv_id)
            if md_content and st.download_button("📝 Markdown", data=md_content, file_name=f"对话_{st.session_state.conv_id}.md", mime="text/markdown", use_container_width=True):
                pass
        with export_col2:
            txt_content = export_text(st.session_state.conv_id)
            if txt_content and st.download_button("📄 纯文本", data=txt_content, file_name=f"对话_{st.session_state.conv_id}.txt", mime="text/plain", use_container_width=True):
                pass

    st.markdown("---")

    # ---- 文档管理 ----
    st.markdown("**📤 上传文档**")
    uploaded = st.file_uploader("选择文件", type=["pdf", "txt", "md", "docx"], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded:
        os.makedirs(DOCUMENTS_DIR, exist_ok=True)
        for f in uploaded:
            with open(os.path.join(DOCUMENTS_DIR, f.name), "wb") as fh:
                fh.write(f.getbuffer())
        st.toast(f"已保存 {len(uploaded)} 个文件", icon="✅")
        st.rerun()

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("🔄 刷新知识库", use_container_width=True, type="primary"):
            with st.spinner("处理中..."):
                if rebuild_knowledge_base():
                    st.toast("知识库已重建！", icon="🎉")
                    st.rerun()
    with col_r2:
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            save_current_conversation()
            st.rerun()

    # 文档列表
    if files:
        st.markdown("**📂 文档列表**")
        for f in files:
            sz_str = f"{f['size']/1024:.1f} KB" if f['size'] > 1024 else f"{f['size']} B"
            colA, colB = st.columns([4, 1])
            with colA:
                st.markdown(f'<div style="font-size:0.8rem;color:rgba(255,255,255,0.8);">{f["name"]}</div>', unsafe_allow_html=True)
            with colB:
                if st.button("✕", key=f"fdel_{f['name']}", help=f"删除 {f['name']}"):
                    delete_file(f["name"])
                    st.rerun()

    # 底部工具
    st.markdown("---")
    with st.expander("⚡ 高级操作"):
        if st.button("🧹 清空向量库 + 重置", use_container_width=True):
            import shutil
            if os.path.exists(VECTOR_STORE_DIR):
                shutil.rmtree(VECTOR_STORE_DIR)
            clear_cache()
            clear_embedding_cache()
            st.session_state.ready = False
            st.session_state.doc_count = 0
            st.toast("已重置", icon="🧹")
            st.rerun()

    st.caption(f"RAG v2.1 | 对话: {st.session_state.conv_id}")


# ===================== 主对话区 =====================

# 当前对话标题
title = st.session_state.conv_title or "新对话"
st.markdown(f"#### 💬 {title}")

if not st.session_state.ready:
    st.info("💡 请先在左侧上传文档，然后点击 **「刷新知识库」** 开始使用")
else:
    # 显示历史消息
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            st.markdown(f'<div class="chat-user">💬 {content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-assistant">🤖 {content}</div>', unsafe_allow_html=True)
            if "sources" in msg and msg["sources"]:
                for s in msg["sources"]:
                    src_label = s.get("source", "文档") if isinstance(s, dict) else "文档"
                    src_content = s.get("content", "") if isinstance(s, dict) else str(s)
                    st.markdown(
                        f'<div class="source-card"><span class="tag">📄 {src_label}</span>{src_content}</div>',
                        unsafe_allow_html=True,
                    )

    # 输入框
    if prompt := st.chat_input("输入你的问题..."):
        # 用户消息
        st.markdown(f'<div class="chat-user">💬 {prompt}</div>', unsafe_allow_html=True)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 流式生成
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                history = st.session_state.messages[:-1]

                for chunk in ask_stream(prompt, chat_history=history):
                    full_response += chunk
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

                if sources_data:
                    for s in sources_data:
                        st.markdown(
                            f'<div class="source-card"><span class="tag">📄 {s.get("source", "文档")}</span>{s.get("content", "")}</div>',
                            unsafe_allow_html=True,
                        )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources_data,
                })

                # 自动保存对话
                save_current_conversation()

            except Exception as e:
                st.error(f"出错了: {e}")
                st.info("点击左侧「刷新知识库」试试")
