"""
Streamlit Web 界面 v3.5
功能：多模型切换 · 混合检索 · 对话搜索 · 用量统计
"""

import os, sys, json, re
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

# ============ CSS ============
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%); }
    .login-box { max-width: 400px; margin: 80px auto; padding: 2rem;
        background: rgba(255,255,255,0.05); border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.1); }
    .header { background: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 100%);
        padding: 1.2rem 2rem; border-radius: 16px; margin-bottom: 1rem; }
    .header h1 { color: white; font-size: 1.4rem; margin: 0; }
    .header p { color: rgba(255,255,255,0.85); font-size: 0.85rem; margin: 0.2rem 0 0; }
    .chat-user { background: linear-gradient(135deg, #6C5CE7 0%, #5B4BD8 100%);
        color: white; padding: 0.7rem 1.1rem; border-radius: 18px 18px 4px 18px;
        max-width: 80%; margin-left: auto; margin-bottom: 0.8rem; }
    .chat-assistant { background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.15);
        color: #E8E8FF; padding: 0.7rem 1.1rem; border-radius: 18px 18px 18px 4px;
        max-width: 92%; margin-right: auto; margin-bottom: 0.8rem; line-height: 1.7;
        font-size: 0.95rem; text-shadow: 0 1px 2px rgba(0,0,0,0.3); }
    .chat-assistant strong, .chat-assistant b { color: #FFFFFF; }
    .chat-assistant code { background: rgba(108,92,231,0.2); color: #C8C0FF;
        padding: 1px 4px; border-radius: 4px; font-size: 0.85em; }
    .chat-assistant a { color: #a29bfe; }
    .source-card { background: rgba(108,92,231,0.08); border: 1px solid rgba(108,92,231,0.15);
        border-radius: 8px; padding: 0.4rem 0.7rem; margin: 0.2rem 0; font-size: 0.75rem; }
    .source-card .tag { background: rgba(108,92,231,0.2); color: #a29bfe;
        padding: 1px 8px; border-radius: 10px; font-size: 0.65rem; margin-right: 6px; }
    .stat-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px; padding: 0.5rem 0.8rem; text-align: center; }
    .stat-card .num { font-size: 1.2rem; font-weight: 700; color: #a29bfe; }
    .stat-card .label { font-size: 0.7rem; color: rgba(255,255,255,0.5); }
    section[data-testid="stSidebar"] { background: rgba(15,15,26,0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.06); }
    .st-bb { border-color: rgba(255,255,255,0.1) !important; }
    div[data-testid="stChatInput"] { background: rgba(255,255,255,0.15) !important;
        border-radius: 24px !important; border: 1px solid rgba(255,255,255,0.25) !important; }
    div[data-testid="stChatInput"] textarea { color: #FFF !important; caret-color: #6C5CE7 !important; }
    #MainMenu, footer { visibility: hidden; }
    .highlight { background: rgba(108,92,231,0.15); padding: 0 2px; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ============ 登录/注册 ============
if not is_authenticated():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("### 🧠 RAG 智能知识库")
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        with st.form("login_form"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("登录", use_container_width=True, type="primary"):
                user = authenticate_user(u, p)
                if user:
                    set_auth(create_session(user.id))
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
    with tab2:
        with st.form("register_form"):
            nu = st.text_input("用户名", key="reg_u")
            np2 = st.text_input("密码", type="password", key="reg_p")
            if st.form_submit_button("注册", use_container_width=True):
                if len(nu) < 2:
                    st.error("用户名至少2个字符")
                elif len(np2) < 6:
                    st.error("密码至少6个字符")
                elif create_user(nu, np2):
                    st.success("注册成功，请登录")
                else:
                    st.error("注册失败")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

user = get_current_user()

# ============ 状态初始化 ============
for key in ["messages", "conv_id", "conv_title", "kb_name", "kb_ready", "kb_doc_count",
            "mode", "upload_key", "available_models", "selected_model", "token_usage", "hybrid_search"]:
    if key not in st.session_state:
        if key == "messages":
            st.session_state[key] = []
        elif key == "token_usage":
            st.session_state[key] = {"total": 0, "history": []}
        elif key == "available_models":
            st.session_state[key] = []
        elif key in ("conv_id", "conv_title", "kb_name", "selected_model"):
            st.session_state[key] = None
        elif key == "hybrid_search":
            st.session_state[key] = True
        elif key == "kb_ready":
            st.session_state[key] = False
        elif key == "kb_doc_count":
            st.session_state[key] = 0
        elif key == "upload_key":
            st.session_state[key] = 0
        elif key == "mode":
            st.session_state[key] = "rag"


# ============ 核心函数 ============
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
    # 清理 BM25 缓存
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
    """从 Ollama 获取可用模型列表"""
    try:
        import requests
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            st.session_state.available_models = models
            if st.session_state.selected_model not in models:
                st.session_state.selected_model = settings.OLLAMA_MODEL if settings.OLLAMA_MODEL in models else (models[0] if models else None)
            return models
    except Exception as e:
        logger.debug(f"获取模型列表失败: {e}")
    return []


# ============ 首次加载 ============
if st.session_state.kb_name is None:
    kbs = list_knowledge_bases()
    switch_kb(kbs[0]["name"]) if kbs else (create_knowledge_base("default", "默认知识库") or switch_kb("default"))
if st.session_state.conv_id is None:
    convs = list_conversations()
    switch_conversation(convs[0]["id"]) if convs else new_conversation()
if not st.session_state.available_models:
    load_available_models()


# ============ 页面标题 ============
st.markdown(f"""
<div class="header">
    <h1>🧠 RAG 智能知识库 <span style="font-size:0.7rem;opacity:0.5;">v3.5</span></h1>
    <p>👋 {user.display_name or user.username} · BM25 混合检索 · 多模型切换 · 对话搜索</p>
</div>""", unsafe_allow_html=True)

current_kb = get_knowledge_base_info(st.session_state.kb_name) if st.session_state.kb_name else None
badge_color = "rgba(0,200,83,0.15);color:#00C853" if st.session_state.kb_ready else "rgba(255,152,0,0.15);color:#FF9800"
st.markdown(f"""<div style="display:flex;gap:0.8rem;margin-bottom:0.8rem;flex-wrap:wrap;align-items:center;">
    <div class="stat-card"><div class="num">{st.session_state.kb_doc_count}</div><div class="label">文档段</div></div>
    <div class="stat-card"><div class="num">{current_kb["doc_count"] if current_kb else 0}</div><div class="label">文件数</div></div>
    <div class="stat-card"><div class="num">{st.session_state.selected_model or settings.OLLAMA_MODEL}</div><div class="label">模型</div></div>
    <div class="stat-card"><div class="num">{st.session_state.token_usage["total"]}</div><div class="label">Token</div></div>
    <span style="display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;font-size:0.75rem;background:{badge_color};">● {"就绪" if st.session_state.kb_ready else "未加载"}</span>
</div>""", unsafe_allow_html=True)


# ============ 侧边栏 ============
with st.sidebar:
    st.markdown(f"**👤 {user.username}**")
    if st.button("🚪 退出", use_container_width=True):
        clear_auth(); st.rerun()
    st.markdown("---")

    # ---- 知识库 ----
    st.markdown("**📚 知识库**")
    for kb in list_knowledge_bases():
        active = kb["name"] == st.session_state.kb_name
        if st.button(f"{'▸ ' if active else '  '}{kb['display_name']} ({kb['doc_count']}文件)", key=f"kb_{kb['name']}", use_container_width=True):
            switch_kb(kb["name"]); st.rerun()

    with st.popover("＋ 新建知识库"):
        nn = st.text_input("标识符", placeholder="my-kb")
        nd = st.text_input("显示名", placeholder="我的知识库")
        if st.button("创建", use_container_width=True, type="primary"):
            safe = re.sub(r'[^a-zA-Z0-9_-]', '', (nn or "").strip())
            if safe and create_knowledge_base(safe, nd or safe, ""):
                switch_kb(safe); st.rerun()
            else:
                st.error("创建失败")

    if current_kb and len(list_knowledge_bases()) > 1:
        if st.button(f"🗑️ 删除 [{current_kb['display_name']}]", use_container_width=True):
            delete_knowledge_base(current_kb["name"])
            remaining = list_knowledge_bases()
            if remaining:
                switch_kb(remaining[0]["name"])
            st.rerun()

    st.markdown("---")

    # ---- 对话 ----
    st.markdown("**💬 对话**")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        if st.button("＋ 新建对话", use_container_width=True):
            new_conversation(); st.rerun()
    with col_b:
        if st.button("💾 保存", use_container_width=True):
            save_current_conv(); st.toast("已保存", icon="✅")

    # 对话搜索
    search_query = st.text_input("🔍 搜索对话", placeholder="搜对话内容...", label_visibility="collapsed")
    convs = list_conversations()
    if search_query:
        sq = search_query.lower()
        convs = [c for c in convs if sq in c["title"].lower()]

    for c in convs[:8]:
        active = c["id"] == st.session_state.conv_id
        cols = st.columns([4, 1])
        with cols[0]:
            if st.button(f"{'▸ ' if active else '  '}{c['title'][:20]}", key=f"c_{c['id']}", use_container_width=True):
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
            if md: st.download_button("📝 MD", md, file_name=f"chat_{st.session_state.conv_id}.md", mime="text/markdown", use_container_width=True)
        with dd:
            if txt: st.download_button("📄 TXT", txt, file_name=f"chat_{st.session_state.conv_id}.txt", mime="text/plain", use_container_width=True)

    st.markdown("---")

    # ---- 文档管理 ----
    kb = st.session_state.kb_name
    if kb:
        st.markdown(f"**📤 上传到 [{current_kb['display_name'] if current_kb else kb}]**")
        uploaded = st.file_uploader("", type=["pdf", "txt", "md", "docx"], accept_multiple_files=True, label_visibility="collapsed", key=f"fu_{st.session_state.upload_key}")
        if uploaded:
            for f in uploaded:
                save_uploaded_file(kb, f.name, f.getbuffer())
            st.session_state.upload_key += 1
            with st.spinner("索引中..."):
                if rebuild_current_kb():
                    st.success("✅ 索引完成")
                else:
                    st.info("文件已保存")
            st.rerun()

        docs = get_documents(kb)
        if docs:
            for doc in docs[:6]:
                cols = st.columns([3, 1])
                with cols[0]:
                    if st.button(f"📄 {doc['name']}", key=f"pv_{doc['name']}", use_container_width=True):
                        with st.expander(doc['name'], expanded=True):
                            st.text(preview_document(kb, doc["name"])[:1500])
                with cols[1]:
                    if st.button("✕", key=f"fd_{doc['name']}"):
                        delete_document(kb, doc["name"]); st.rerun()

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🔄 刷新索引", use_container_width=True, type="primary"):
                with st.spinner("重建中..."):
                    if rebuild_current_kb():
                        st.success("重建完成！"); st.rerun()
        with col_r2:
            if st.button("🗑️ 清空", use_container_width=True):
                st.session_state.messages = []; st.rerun()

    st.markdown("---")

    # ---- 模型选择 + 模式切换 ----
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("**🤖 模型**")
        models = st.session_state.available_models
        if models:
            idx = 0
            if st.session_state.selected_model in models:
                idx = models.index(st.session_state.selected_model)
            selected = st.selectbox("", models, index=idx, label_visibility="collapsed", key="model_sel")
            if selected != st.session_state.selected_model:
                st.session_state.selected_model = selected
                # 更新运行时模型
                os.environ["OLLAMA_MODEL"] = selected
                from app.rag.engine import get_llm, clear_llm_cache
                clear_llm_cache()
                st.rerun()
        else:
            st.caption(st.session_state.selected_model or settings.OLLAMA_MODEL)

    with col_m2:
        st.markdown("**⚡ 模式**")
        mode = st.radio("", ["rag", "agent"], format_func=lambda x: {"rag":"📚RAG","agent":"🤖Agent"}[x],
                        index=0 if st.session_state.mode=="rag" else 1, label_visibility="collapsed")
        if mode != st.session_state.mode:
            st.session_state.mode = mode; st.rerun()

    # 混合检索开关
    hybrid = st.toggle("🔀 混合检索（BM25+向量）", value=st.session_state.hybrid_search)
    st.session_state.hybrid_search = hybrid
    st.caption(f"v3.5 | KB: {st.session_state.kb_name}")


# ============ 主对话区 ============
title = st.session_state.conv_title or "新对话"
kb_display = current_kb["display_name"] if current_kb else "未选择"
mode_icon = "📚RAG" if st.session_state.mode == "rag" else "🤖Agent"
st.markdown(f"#### 💬 {title}  ·  `{kb_display}` · `{mode_icon}`")

for msg in st.session_state.messages:
    role, content = msg["role"], msg["content"]
    if role == "user":
        st.markdown(f'<div class="chat-user">💬 {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-assistant">🤖 {content}</div>', unsafe_allow_html=True)
        if "sources" in msg and msg["sources"]:
            for s in msg["sources"]:
                src = s.get("source","文档") if isinstance(s,dict) else "文档"
                txt = s.get("content","") if isinstance(s,dict) else str(s)
                st.markdown(f'<div class="source-card"><span class="tag">📄 {src}</span>{txt}</div>', unsafe_allow_html=True)

if prompt := st.chat_input("输入你的问题..."):
    st.markdown(f'<div class="chat-user">💬 {prompt}</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.token_usage["total"] += len(prompt)

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
                    placeholder.markdown(f'<div class="chat-assistant">🤖 {full}▌</div>', unsafe_allow_html=True)

                answer = full
                sources = []
                if "__SOURCES__:" in answer:
                    parts = answer.split("__SOURCES__:")
                    answer = parts[0]
                    try:
                        sources = json.loads(parts[1])
                    except json.JSONDecodeError:
                        sources = []

                placeholder.markdown(f'<div class="chat-assistant">🤖 {answer}</div>', unsafe_allow_html=True)
                if sources:
                    for s in sources:
                        st.markdown(f'<div class="source-card"><span class="tag">📄 {s.get("source","文档")}</span>{s.get("content","")}</div>', unsafe_allow_html=True)
                st.session_state.messages.append({"role":"assistant","content":answer,"sources":sources})
                st.session_state.token_usage["total"] += len(answer)

            elif mode == "agent" or not st.session_state.kb_ready:
                with st.spinner("🤔 思考中..."):
                    if mode == "agent":
                        from query import clean_deepseek_output
                        res = ask_agent(prompt, vector_dir=vec_dir if st.session_state.kb_ready else None, chat_history=history)
                        answer = clean_deepseek_output(res["answer"])
                        tag = {"rag":"📚知识库","web":"🌐联网","direct":"💡回答"}.get(res["mode"],"🤖Agent")
                        display = f"{answer}\n\n<sup style='color:rgba(255,255,255,0.3);font-size:0.7rem;'>回答: {tag}</sup>"
                        placeholder.markdown(f'<div class="chat-assistant">🤖 {display}</div>', unsafe_allow_html=True)
                        st.session_state.messages.append({"role":"assistant","content":answer + f"\n*({tag})*"})
                    else:
                        from query import get_llm, clean_deepseek_output
                        raw = get_llm().invoke(prompt).content
                        answer = clean_deepseek_output(raw)
                        placeholder.markdown(f'<div class="chat-assistant">🤖 {answer}</div>', unsafe_allow_html=True)
                        st.session_state.messages.append({"role":"assistant","content":answer + "\n*（离线回答）*"})
                    st.session_state.token_usage["total"] += len(answer)

            save_current_conv()

        except Exception as e:
            logger.error(f"问答出错: {e}", exc_info=True)
            st.error(f"出错了: {e}")
