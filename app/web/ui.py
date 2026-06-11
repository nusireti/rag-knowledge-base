"""
🦝 RAG 智能知识库 v4.0
清爽亮色设计 · 多模型 · 混合检索 · 对话搜索
"""

import os, sys, json, re, time, secrets
from pathlib import Path
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st
from app.config import settings
from app.logger import logger
from app.auth import authenticate_user, create_user, create_session
from app.web.state import get_current_user, is_authenticated, set_auth, clear_auth
from app.rag.engine import ask_stream, clear_llm_cache
from app.rag.ingest import load_all_documents, split_documents, build_vector_store
from app.rag.embed import clear_embedding_cache
from agent_tools import ask_agent
from kb_manager import (
    list_knowledge_bases, create_knowledge_base, delete_knowledge_base,
    get_knowledge_base_info, get_documents, delete_document,
    save_uploaded_file, get_documents_dir, get_vector_store_dir, preview_document,
)
from chat_history import (
    list_conversations, create_conversation, load_conversation,
    save_messages, delete_conversation, export_markdown, export_text,
)
from app.database import init_db; init_db()
from app.models import User

# ===================== 全局样式 =====================
PAGE_CSS = """
<style>
    /* ===== 字体 ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    code, pre { font-family: 'JetBrains Mono', monospace !important; }

    /* ===== 全局亮色 ===== */
    .stApp {
        background: #F5F5FA;
        background-image:
            radial-gradient(ellipse 80% 60% at 50% 0%, rgba(124,92,252,0.04) 0%, transparent 60%);
    }
    section[data-testid="stSidebar"] {
        background: #FFFFFF !important;
        border-right: 1px solid rgba(0,0,0,0.06);
    }
    section[data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        border: none !important;
        color: #555 !important;
        text-align: left !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: rgba(124,92,252,0.08) !important;
        color: #7C5CFC !important;
    }

    /* ===== 卡片 ===== */
    .glass-card {
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        transition: all 0.3s ease;
    }
    .glass-card:hover { box-shadow: 0 4px 20px rgba(124,92,252,0.1); border-color: rgba(124,92,252,0.2); }

    /* ===== 头部 ===== */
    .app-header {
        background: linear-gradient(135deg, #7C5CFC 0%, #9D8BFF 100%);
        border-radius: 16px;
        padding: 1.2rem 1.8rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(124,92,252,0.2);
    }
    .app-header h1 { color: #FFFFFF; font-weight: 700; font-size: 1.3rem; margin: 0; letter-spacing: -0.02em; }
    .app-header p { color: rgba(255,255,255,0.75); font-size: 0.8rem; margin: 0.2rem 0 0 0; }

    /* ===== 统计卡片 ===== */
    .stat-row { display: flex; gap: 0.6rem; margin-bottom: 0.8rem; flex-wrap: wrap; }
    .stat-item {
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 10px;
        padding: 0.4rem 0.8rem;
        text-align: center;
        min-width: 60px;
        flex: 1;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    }
    .stat-item .num { font-size: 1.1rem; font-weight: 700; color: #7C5CFC; }
    .stat-item .label { font-size: 0.65rem; color: rgba(0,0,0,0.35);
        text-transform: uppercase; letter-spacing: 0.04em; }
    .status-badge {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 4px 14px; border-radius: 20px; font-size: 0.7rem;
        font-weight: 500;
    }

    /* ===== 对话气泡 ===== */
    .chat-msg {
        padding: 0.8rem 1.2rem;
        border-radius: 16px;
        margin-bottom: 0.6rem;
        line-height: 1.7;
        font-size: 0.92rem;
        animation: msgIn 0.3s ease;
    }
    @keyframes msgIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .chat-user {
        background: linear-gradient(135deg, #7C5CFC 0%, #6A4AE8 100%);
        color: white;
        border-radius: 18px 18px 4px 18px;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 2px 8px rgba(124,92,252,0.2);
    }
    .chat-assistant {
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.06);
        color: #333;
        border-radius: 18px 18px 18px 4px;
        max-width: 92%;
        margin-right: auto;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .chat-assistant strong, .chat-assistant b { color: #1A1A2E; }
    .chat-assistant code {
        background: rgba(124,92,252,0.1);
        color: #7C5CFC;
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 0.85em;
    }
    .chat-assistant pre {
        background: #F5F5FA !important;
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 10px;
        padding: 0.8rem !important;
        overflow-x: auto;
    }
    .chat-assistant a { color: #7C5CFC; }

    /* ===== 来源卡片 ===== */
    .source-card {
        background: rgba(124,92,252,0.04);
        border: 1px solid rgba(124,92,252,0.1);
        border-radius: 8px;
        padding: 0.4rem 0.7rem;
        margin: 0.2rem 0;
        font-size: 0.72rem;
        color: #666;
        transition: all 0.2s;
    }
    .source-card:hover {
        background: rgba(124,92,252,0.08);
        border-color: rgba(124,92,252,0.2);
    }
    .source-tag {
        background: rgba(124,92,252,0.1);
        color: #7C5CFC;
        padding: 1px 8px;
        border-radius: 10px;
        font-size: 0.6rem;
        font-weight: 600;
        margin-right: 6px;
        white-space: nowrap;
    }

    /* ===== 输入框 ===== */
    div[data-testid="stChatInput"] {
        background: #FFFFFF !important;
        border-radius: 24px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: rgba(124,92,252,0.4) !important;
        box-shadow: 0 2px 12px rgba(124,92,252,0.12) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #333 !important;
        caret-color: #7C5CFC !important;
        font-size: 0.9rem !important;
    }

    /* ===== 按钮 ===== */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #7C5CFC 0%, #6A4AE8 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(124,92,252,0.3) !important;
    }

    /* ===== tabs ===== */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(0,0,0,0.03) !important;
        border-radius: 8px !important;
        padding: 6px 14px !important;
        font-size: 0.8rem;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(124,92,252,0.1) !important;
        color: #7C5CFC !important;
    }

    /* ===== inputs/select ===== */
    .stSelectbox div[data-baseweb="select"] > div,
    .stTextInput input, .stTextArea textarea {
        background: #FFFFFF !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        border-radius: 10px !important;
        color: #333 !important;
    }

    /* ===== toggle ===== */
    .stToggle label span { color: #666 !important; }

    /* ===== scrollbar ===== */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.2); }

    /* ===== hide clutter ===== */
    #MainMenu, footer { visibility: hidden; display: none; }
    header[data-testid="stHeader"] { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    .stApp > header { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    button[kind="header"] { display: none !important; }

    /* ===== login box ===== */
    .login-box {
        max-width: 400px;
        margin: 100px auto;
        padding: 2.5rem;
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.06);
    }
    .login-box h2 { color: #1A1A2E; text-align: center; margin-bottom: 1.5rem; font-weight: 700; }

    /* ===== section divider ===== */
    .section-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: rgba(0,0,0,0.3);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 1rem 0 0.6rem 0;
        padding: 0 4px;
    }

    /* ===== token bar ===== */
    .token-bar {
        height: 3px;
        background: rgba(0,0,0,0.06);
        border-radius: 2px;
        overflow: hidden;
    }
    .token-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #7C5CFC, #9D8BFF);
        border-radius: 2px;
        transition: width 0.5s ease;
    }

    /* ===== conversation item ===== */
    .conv-item {
        display: flex; align-items: center; justify-content: space-between;
        padding: 6px 8px; border-radius: 8px; cursor: pointer; transition: all 0.15s;
    }
    .conv-item:hover { background: rgba(124,92,252,0.06); }
    .conv-item.active { background: rgba(124,92,252,0.1);
        border: 1px solid rgba(124,92,252,0.12); }
    .conv-item .title { font-size: 0.82rem; color: #555; overflow: hidden;
        text-overflow: ellipsis; white-space: nowrap; }
</style>
"""


# ===================== 会话状态初始化 =====================
def init_state():
    keys = {
        "messages": [],
        "conv_id": None,
        "conv_title": "新对话",
        "kb_name": None,
        "kb_ready": False,
        "kb_doc_count": 0,
        "mode": "rag",
        "upload_key": 0,
        "available_models": [],
        "selected_model": None,
        "token_usage": {"total": 0, "history": [], "daily": 0},
        "hybrid_search": True,
        "provider": settings.LLM_PROVIDER,
        "last_rerun": 0,
    }
    for k, v in keys.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ===================== 核心功能 =====================
def switch_kb(kb_name):
    st.session_state.kb_name = kb_name
    st.session_state.kb_ready = False
    st.session_state.kb_doc_count = 0
    vec_dir = get_vector_store_dir(kb_name)
    if os.path.exists(vec_dir) and any(os.scandir(vec_dir)):
        try:
            st.session_state.kb_ready = True
            docs = load_all_documents(get_documents_dir(kb_name))
            st.session_state.kb_doc_count = len(docs) if docs else 0
        except Exception:
            pass


def rebuild_current_kb():
    kb = st.session_state.kb_name
    if not kb:
        return False
    clear_llm_cache()
    clear_embedding_cache()
    docs_dir = get_documents_dir(kb)
    vec_dir = get_vector_store_dir(kb)
    documents = load_all_documents(docs_dir)
    if not documents:
        return False
    chunks = split_documents(documents)
    build_vector_store(chunks, vec_dir, overwrite=True)
    bm25_cache = Path(vec_dir) / "bm25_index.pkl"
    if bm25_cache.exists():
        bm25_cache.unlink()
    st.session_state.kb_ready = True
    st.session_state.kb_doc_count = len(documents)
    return True


def switch_conversation(conv_id):
    st.session_state.conv_id = conv_id
    msgs = load_conversation(conv_id)
    st.session_state.messages = msgs if msgs else []
    for c in list_conversations():
        if c["id"] == conv_id:
            st.session_state.conv_title = c["title"]
            break


def new_conversation():
    cid = create_conversation()
    st.session_state.conv_id = cid
    st.session_state.conv_title = "新对话"
    st.session_state.messages = []


def save_current_conv():
    if st.session_state.conv_id and st.session_state.messages:
        save_messages(st.session_state.conv_id, st.session_state.messages)


def load_available_models():
    try:
        import requests
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            st.session_state.available_models = models
            if st.session_state.selected_model not in models:
                st.session_state.selected_model = (
                    settings.OLLAMA_MODEL if settings.OLLAMA_MODEL in models
                    else (models[0] if models else None)
                )
            return models
    except Exception as e:
        logger.debug(f"获取模型列表失败: {e}")
    return []


# ===================== 页面 =====================
st.set_page_config(page_title="RAG 智能知识库", page_icon="🦝", layout="wide")
st.markdown(PAGE_CSS, unsafe_allow_html=True)

init_state()

# ---------- 登录 ----------
if not is_authenticated():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("<h2>🦝 RAG 智能知识库</h2>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        with st.form("login_form"):
            u = st.text_input("用户名", placeholder="输入用户名")
            p = st.text_input("密码", type="password", placeholder="输入密码")
            if st.form_submit_button("登录", use_container_width=True, type="primary"):
                user = authenticate_user(u, p)
                if user:
                    set_auth(create_session(user.id))
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
    with tab2:
        with st.form("register_form"):
            nu = st.text_input("用户名", key="reg_u", placeholder="至少2个字符")
            ne = st.text_input("邮箱", key="reg_e", placeholder="用于验证和找回密码")
            show_vcode = settings.SMTP_ENABLE and ne
            vcode = ""
            if show_vcode:
                cv1, cv2 = st.columns([3, 1])
                with cv1:
                    vcode = st.text_input("验证码", key="reg_v", placeholder="输入邮箱收到的验证码")
                with cv2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("📨 发送验证码", key="send_vcode", use_container_width=True):
                        from app.verify import send_verify_code
                        st.success("已发送" if send_verify_code(ne) else "发送失败")
            np1 = st.text_input("密码", type="password", key="reg_p1", placeholder="至少6个字符")
            np2 = st.text_input("确认密码", type="password", key="reg_p2", placeholder="再次输入密码")
            if st.form_submit_button("注册", use_container_width=True, type="primary"):
                errs = []
                if len(nu) < 2: errs.append("用户名至少2个字符")
                if len(np1) < 6: errs.append("密码至少6个字符")
                if np1 != np2: errs.append("两次密码不一致")
                if errs:
                    for e in errs: st.error(e)
                elif ne and show_vcode and not vcode:
                    st.error("请输入验证码")
                elif ne and show_vcode:
                    from app.verify import verify_code
                    if not verify_code(ne, vcode):
                        st.error("验证码错误")
                    elif create_user(nu, np1, ne):
                        st.success("注册成功，请登录！")
                    else:
                        st.error("注册失败")
                elif create_user(nu, np1, ne):
                    st.success("注册成功，请登录！")
                else:
                    st.error("注册失败")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

user = get_current_user()

# ---------- 首次加载 ----------
if st.session_state.kb_name is None:
    kbs = list_knowledge_bases()
    if kbs:
        switch_kb(kbs[0]["name"])
    else:
        create_knowledge_base("default", "默认知识库")
        switch_kb("default")
if st.session_state.conv_id is None:
    convs = list_conversations()
    if convs:
        switch_conversation(convs[0]["id"])
    else:
        new_conversation()
if not st.session_state.available_models:
    load_available_models()

# ---------- 头部 ----------
st.markdown(f"""
<div class="app-header">
    <h1>🦝 RAG 智能知识库 <span style="font-size:0.65rem;opacity:0.35;font-weight:500;">v4.0</span></h1>
    <p>👋 {user.display_name or user.username} · BM25 混合检索 · 多模型切换 · 对话搜索</p>
</div>""", unsafe_allow_html=True)

# 统计行
current_kb = get_knowledge_base_info(st.session_state.kb_name) if st.session_state.kb_name else None
kb_ready = st.session_state.kb_ready
badge_cls = "status-badge"
badge_style = "background:rgba(0,200,83,0.1);color:#00C853;border:1px solid rgba(0,200,83,0.15)" if kb_ready else "background:rgba(255,152,0,0.1);color:#FF9800;border:1px solid rgba(255,152,0,0.15)"
doc_count = st.session_state.kb_doc_count
file_count = current_kb["doc_count"] if current_kb else 0
model_name = st.session_state.selected_model or settings.OLLAMA_MODEL
total_tokens = st.session_state.token_usage["total"]

st.markdown(f"""
<div class="stat-row">
    <div class="stat-item"><div class="num">{doc_count}</div><div class="label">文档段</div></div>
    <div class="stat-item"><div class="num">{file_count}</div><div class="label">文件数</div></div>
    <div class="stat-item"><div class="num" style="font-size:0.8rem;">{model_name[:12]}</div><div class="label">模型</div></div>
    <div class="stat-item"><div class="num">{total_tokens}</div><div class="label">Token</div></div>
    <div class="stat-item" style="flex:0;min-width:auto;">
        <span class="{badge_cls}" style="{badge_style}">● {"就绪" if kb_ready else "未加载"}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Token 使用率
MAX_TOKENS = 100000
pct = min(total_tokens / MAX_TOKENS * 100, 100)
st.markdown(f"""
<div class="token-bar">
    <div class="token-bar-fill" style="width:{pct}%;"></div>
</div>
""", unsafe_allow_html=True)

# ---------- 侧边栏 ----------
with st.sidebar:
    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
                f"<span style='font-size:1.5rem;'>👤</span>"
                f"<span style='font-weight:600;color:#1A1A2E;'>{user.username}</span></div>",
                unsafe_allow_html=True)
    if st.button("🚪 退出", use_container_width=True):
        clear_auth(); st.rerun()
    st.markdown("---")

    # ---- 知识库 ----
    st.markdown('<div class="section-title">📚 知识库</div>', unsafe_allow_html=True)
    for kb in list_knowledge_bases():
        active = kb["name"] == st.session_state.kb_name
        prefix = "▸" if active else " "
        if st.button(f"{prefix} {kb['display_name']} ({kb['doc_count']})",
                     key=f"kb_{kb['name']}", use_container_width=True):
            switch_kb(kb["name"]); st.rerun()

    with st.expander("＋ 新建", expanded=False):
        nn = st.text_input("标识符", placeholder="my-kb", label_visibility="collapsed")
        nd = st.text_input("显示名", placeholder="我的知识库", label_visibility="collapsed")
        if st.button("创建", use_container_width=True, type="primary"):
            safe = re.sub(r'[^a-zA-Z0-9_-]', '', (nn or "").strip())
            if safe and create_knowledge_base(safe, nd or safe, ""):
                switch_kb(safe); st.rerun()

    if current_kb and len(list_knowledge_bases()) > 1:
        if st.button(f"🗑️ [{current_kb['display_name']}]", use_container_width=True):
            delete_knowledge_base(current_kb["name"])
            remaining = list_knowledge_bases()
            if remaining:
                switch_kb(remaining[0]["name"])
            st.rerun()

    st.markdown("---")

    # ---- 对话 ----
    st.markdown('<div class="section-title">💬 对话</div>', unsafe_allow_html=True)
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        if st.button("＋ 新建", use_container_width=True):
            new_conversation(); st.rerun()
    with cc2:
        if st.button("💾 保存", use_container_width=True):
            save_current_conv(); st.toast("已保存", icon="✅")

    search_query = st.text_input("🔍", placeholder="搜对话...", label_visibility="collapsed")
    convs = list_conversations()
    if search_query:
        sq = search_query.lower()
        convs = [c for c in convs if sq in c["title"].lower()]

    for c in convs[:8]:
        active = c["id"] == st.session_state.conv_id
        act_cls = "active" if active else ""
        st.markdown(f"""
        <div class="conv-item {act_cls}" onclick="console.log('click')">
            <span class="title">{'▸ ' if active else '  '}{c['title'][:20]}</span>
        </div>""", unsafe_allow_html=True)
        cols = st.columns([4, 1])
        with cols[0]:
            if st.button(f"{'▸ ' if active else '  '}{c['title'][:20]}",
                         key=f"c_{c['id']}", use_container_width=True):
                switch_conversation(c["id"]); st.rerun()
        with cols[1]:
            if st.button("✕", key=f"dc_{c['id']}"):
                delete_conversation(c["id"])
                if c["id"] == st.session_state.conv_id:
                    remaining = list_conversations()
                    switch_conversation(remaining[0]["id"]) if remaining else new_conversation()
                st.rerun()

    if st.session_state.messages:
        md = export_markdown(st.session_state.conv_id)
        txt = export_text(st.session_state.conv_id)
        cc, dd = st.columns(2)
        with cc:
            if md: st.download_button("📝 MD", md, file_name=f"chat_{st.session_state.conv_id}.md",
                                       mime="text/markdown", use_container_width=True)
        with dd:
            if txt: st.download_button("📄 TXT", txt, file_name=f"chat_{st.session_state.conv_id}.txt",
                                       mime="text/plain", use_container_width=True)

    st.markdown("---")

    # ---- 文档上传 ----
    kb = st.session_state.kb_name
    if kb:
        st.markdown(f'<div class="section-title">📤 上传</div>', unsafe_allow_html=True)
        st.caption(f"到 [{current_kb['display_name'] if current_kb else kb}]")
        uploaded = st.file_uploader(
            "", type=["pdf", "txt", "md", "docx"],
            accept_multiple_files=True, label_visibility="collapsed",
            key=f"fu_{st.session_state.upload_key}"
        )
        if uploaded:
            for f in uploaded:
                try:
                    save_uploaded_file(kb, f.name, f.getbuffer())
                except ValueError as e:
                    st.error(f"文件上传失败: {e}")
                    st.stop()
            st.session_state.upload_key += 1
            with st.spinner("🔄 索引中..."):
                if rebuild_current_kb():
                    st.success("✅ 索引完成")
                else:
                    st.info("文件已保存")
            st.rerun()

        docs = get_documents(kb)
        if docs:
            with st.expander(f"📄 文件 ({len(docs)})", expanded=False):
                for doc in docs[:6]:
                    cols = st.columns([3, 1])
                    with cols[0]:
                        if st.button(f"📄 {doc['name']}", key=f"pv_{doc['name']}",
                                     use_container_width=True):
                            with st.expander(doc['name'], expanded=True):
                                st.text(preview_document(kb, doc["name"])[:1500])
                    with cols[1]:
                        if st.button("✕", key=f"fd_{doc['name']}"):
                            delete_document(kb, doc["name"]); st.rerun()

        cr1, cr2 = st.columns(2)
        with cr1:
            if st.button("🔄 刷新索引", use_container_width=True, type="primary"):
                with st.spinner("重建中..."):
                    st.success("✅ 重建完成") if rebuild_current_kb() else st.warning("⚠️ 失败")
                st.rerun()
        with cr2:
            if st.button("🗑️ 清空", use_container_width=True):
                st.session_state.messages = []; st.rerun()

    st.markdown("---")

    # ---- 提供商 + 模型 + 模式 ----
    cp1, cp2, cp3, cp4 = st.columns(4)
    with cp1:
        st.markdown('<div class="section-title">🏭 提供商</div>', unsafe_allow_html=True)
    with cp2:
        st.markdown('<div class="section-title">🤖 模型</div>', unsafe_allow_html=True)
    with cp3:
        st.markdown('<div class="section-title">⚡ 模式</div>', unsafe_allow_html=True)
    with cp4:
        st.markdown('<div class="section-title">🔀 混合</div>', unsafe_allow_html=True)

    cp1, cp2, cp3, cp4 = st.columns(4)
    with cp1:
        provider = st.selectbox(
            "", ["local", "openai", "dashscope"],
            index=["local", "openai", "dashscope"].index(
                getattr(st.session_state, "provider", settings.LLM_PROVIDER)
            ),
            format_func=lambda x: {"local": "🖥️ Ollama", "openai": "🔵 OpenAI",
                                    "dashscope": "🟣 通义/文心"}[x],
            label_visibility="collapsed", key="provider_sel"
        )
        if provider != st.session_state.get("provider"):
            st.session_state.provider = provider
            os.environ["LLM_PROVIDER"] = provider
            os.environ["EMBEDDING_PROVIDER"] = provider
            clear_llm_cache()
            st.rerun()
    with cp2:
        models = st.session_state.available_models
        if models:
            idx = 0
            if st.session_state.selected_model in models:
                idx = models.index(st.session_state.selected_model)
            selected = st.selectbox("", models, index=idx, label_visibility="collapsed",
                                     key="model_sel")
            if selected != st.session_state.selected_model:
                st.session_state.selected_model = selected
                os.environ["OLLAMA_MODEL"] = selected
                clear_llm_cache()
                st.rerun()
        else:
            st.caption(st.session_state.selected_model or settings.OLLAMA_MODEL)
    with cm2:
        mode = st.radio("", ["rag", "agent"],
                         format_func=lambda x: {"rag": "📚RAG", "agent": "🤖Agent"}[x],
                         index=0 if st.session_state.mode == "rag" else 1,
                         label_visibility="collapsed")
        if mode != st.session_state.mode:
            st.session_state.mode = mode; st.rerun()
    with cm3:
        hybrid = st.toggle("🔀", value=st.session_state.hybrid_search)
        st.session_state.hybrid_search = hybrid

    st.caption(f"KB: {st.session_state.kb_name} · v4.0")

# ---------- 主对话区 ----------
title = st.session_state.conv_title or "新对话"
kb_display = current_kb["display_name"] if current_kb else "未选择"
mode_icon = "📚RAG" if st.session_state.mode == "rag" else "🤖Agent"
st.markdown(f"#### 💬 {title}", unsafe_allow_html=True)
st.caption(f"`{kb_display}` · `{mode_icon}`")

# 消息气泡
for msg in st.session_state.messages:
    role, content = msg["role"], msg["content"]
    if role == "user":
        st.markdown(f'<div class="chat-msg chat-user">💬 {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-msg chat-assistant">🤖 {content}</div>', unsafe_allow_html=True)
        if "sources" in msg and msg["sources"]:
            for s in msg["sources"]:
                src = s.get("source", "文档") if isinstance(s, dict) else "文档"
                txt = s.get("content", "") if isinstance(s, dict) else str(s)
                st.markdown(
                    f'<div class="source-card">'
                    f'<span class="source-tag">📄 {src}</span>{txt}</div>',
                    unsafe_allow_html=True,
                )

# 输入
if prompt := st.chat_input("输入你的问题..."):
    st.markdown(f'<div class="chat-msg chat-user">💬 {prompt}</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.token_usage["total"] += len(prompt)
    st.session_state.token_usage["daily"] += len(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            vec_dir = get_vector_store_dir(st.session_state.kb_name) if st.session_state.kb_name else None
            history = st.session_state.messages[:-1]
            mode = st.session_state.mode

            if mode == "rag" and st.session_state.kb_ready:
                full = ""
                for chunk in ask_stream(prompt, chat_history=history, vector_dir=vec_dir):
                    full += chunk
                    if "__SOURCES__:" in full:
                        break
                    placeholder.markdown(
                        f'<div class="chat-msg chat-assistant">🤖 {full}▌</div>',
                        unsafe_allow_html=True,
                    )
                answer = full
                sources = []
                if "__SOURCES__:" in answer:
                    parts = answer.split("__SOURCES__:")
                    answer = parts[0]
                    try:
                        sources = json.loads(parts[1])
                    except json.JSONDecodeError:
                        sources = []

                placeholder.markdown(
                    f'<div class="chat-msg chat-assistant">🤖 {answer}</div>',
                    unsafe_allow_html=True,
                )
                if sources:
                    for s in sources:
                        st.markdown(
                            f'<div class="source-card">'
                            f'<span class="source-tag">📄 {s.get("source","文档")}</span>'
                            f'{s.get("content","")}</div>',
                            unsafe_allow_html=True,
                        )
                st.session_state.messages.append({
                    "role": "assistant", "content": answer, "sources": sources
                })
                st.session_state.token_usage["total"] += len(answer)
                st.session_state.token_usage["daily"] += len(answer)
                st.session_state.token_usage["history"].append({
                    "q": prompt[:30], "tokens": len(answer), "t": time.time()
                })

            elif mode == "agent" or not st.session_state.kb_ready:
                with st.spinner("🤔 思考中..."):
                    if mode == "agent":
                        from query import clean_deepseek_output
                        res = ask_agent(prompt, vector_dir=vec_dir if st.session_state.kb_ready else None,
                                        chat_history=history)
                        answer = clean_deepseek_output(res["answer"])
                        tag = {"rag": "📚知识库", "web": "🌐联网", "direct": "💡回答"}.get(
                            res["mode"], "🤖Agent"
                        )
                        display = f"{answer}\n\n<sup style='color:rgba(0,0,0,0.3);font-size:0.65rem;'>回答: {tag}</sup>"
                        placeholder.markdown(
                            f'<div class="chat-msg chat-assistant">🤖 {display}</div>',
                            unsafe_allow_html=True,
                        )
                        st.session_state.messages.append({
                            "role": "assistant", "content": answer + f"\n*({tag})*"
                        })
                    else:
                        from query import get_llm, clean_deepseek_output
                        raw = get_llm().invoke(prompt).content
                        answer = clean_deepseek_output(raw)
                        placeholder.markdown(
                            f'<div class="chat-msg chat-assistant">🤖 {answer}</div>',
                            unsafe_allow_html=True,
                        )
                        st.session_state.messages.append({
                            "role": "assistant", "content": answer + "\n*（离线回答）*"
                        })
                    st.session_state.token_usage["total"] += len(answer)
                    st.session_state.token_usage["history"].append({
                        "q": prompt[:30], "tokens": len(answer), "t": time.time()
                    })

            save_current_conv()

        except Exception as e:
            logger.error(f"问答出错: {e}", exc_info=True)
            st.error(f"出错了: {e}")
