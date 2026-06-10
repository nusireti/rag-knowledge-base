"""
Streamlit Web 界面
融合旧版完整功能 + 用户认证 + 数据库持久化
"""

import os
import sys
import json
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from app.config import settings
from app.logger import logger
from app.auth import authenticate_user, create_user, create_session
from app.web.state import get_current_user, is_authenticated, set_auth, clear_auth
from app.rag.engine import ask_stream, clear_llm_cache, clear_vector_store_cache
from app.rag.ingest import load_all_documents, split_documents, build_vector_store, ingest_documents
from app.rag.embed import clear_embedding_cache
from agent_tools import ask_agent
from kb_manager import (
    list_knowledge_bases, create_knowledge_base, delete_knowledge_base,
    get_knowledge_base_info, get_documents, delete_document,
    save_uploaded_file, get_documents_dir, get_vector_store_dir,
    preview_document,
)
from chat_history import (
    list_conversations, create_conversation, load_conversation,
    save_messages, delete_conversation, export_markdown, export_text,
)
from app.database import get_db, init_db
from app.models import User, KnowledgeBase

# 初始化数据库
init_db()

# ===================== CSS =====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%); }
    .login-box { max-width: 400px; margin: 80px auto; padding: 2rem;
        background: rgba(255,255,255,0.05); border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.1); }
    .header {
        background: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 100%);
        padding: 1.2rem 2rem; border-radius: 16px; margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(108,92,231,0.3);
    }
    .header h1 { color: white; font-weight: 700; font-size: 1.4rem; margin: 0; }
    .header p { color: rgba(255,255,255,0.85); font-size: 0.85rem; margin: 0.2rem 0 0; }
    .stat-card {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px; padding: 0.5rem 0.8rem; text-align: center;
    }
    .stat-card .num { font-size: 1.2rem; font-weight: 700; color: #a29bfe; }
    .stat-card .label { font-size: 0.7rem; color: rgba(255,255,255,0.5); }
    .chat-user {
        background: linear-gradient(135deg, #6C5CE7 0%, #5B4BD8 100%);
        color: white; padding: 0.7rem 1.1rem;
        border-radius: 18px 18px 4px 18px; max-width: 80%;
        margin-left: auto; margin-bottom: 0.8rem; font-size: 0.95rem;
    }
    .chat-assistant {
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
        padding: 0.7rem 1.1rem; border-radius: 18px 18px 18px 4px;
        max-width: 92%; margin-right: auto; margin-bottom: 0.8rem; line-height: 1.6;
    }
    .source-card {
        background: rgba(108,92,231,0.08); border: 1px solid rgba(108,92,231,0.15);
        border-radius: 8px; padding: 0.4rem 0.7rem; margin: 0.2rem 0; font-size: 0.75rem;
    }
    .source-card .tag {
        background: rgba(108,92,231,0.2); color: #a29bfe;
        padding: 1px 8px; border-radius: 10px; font-size: 0.65rem; margin-right: 6px;
    }
    section[data-testid="stSidebar"] { background: rgba(15,15,26,0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.06); }
    div[data-testid="stChatInput"] {
        background: rgba(255,255,255,0.15) !important; border-radius: 24px !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
    }
    div[data-testid="stChatInput"] textarea { color: #FFFFFF !important; caret-color: #6C5CE7 !important; }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #6C5CE7 !important; box-shadow: 0 0 0 3px rgba(108,92,231,0.3) !important;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ===================== 登录/注册 =====================

def render_login_page():
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("### 🧠 RAG 智能知识库")
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        with st.form("login_form"):
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.form_submit_button("登录", use_container_width=True, type="primary"):
                if not u or not p:
                    st.error("请输入用户名和密码")
                else:
                    user = authenticate_user(u, p)
                    if user:
                        set_auth(create_session(user.id))
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
    with tab2:
        with st.form("register_form"):
            nu = st.text_input("用户名", key="reg_u")
            np = st.text_input("密码", type="password", key="reg_p")
            np2 = st.text_input("确认密码", type="password", key="reg_p2")
            if st.form_submit_button("注册", use_container_width=True):
                if not nu or len(nu) < 2:
                    st.error("用户名至少2个字符")
                elif not np or len(np) < 6:
                    st.error("密码至少6个字符")
                elif np != np2:
                    st.error("两次密码不一致")
                elif create_user(nu, np):
                    st.success("注册成功，请登录")
                else:
                    st.error("注册失败，用户名可能已存在")
    st.markdown('</div>', unsafe_allow_html=True)


if not is_authenticated():
    render_login_page()
    st.stop()

user = get_current_user()

# ===================== 状态初始化 =====================
for key in ["messages", "conv_id", "conv_title", "kb_name", "kb_ready", "kb_doc_count", "mode", "upload_key"]:
    if key not in st.session_state:
        if key in ("messages",):
            st.session_state[key] = []
        elif key in ("conv_id", "conv_title", "kb_name"):
            st.session_state[key] = None
        elif key == "kb_ready":
            st.session_state[key] = False
        elif key == "kb_doc_count":
            st.session_state[key] = 0
        elif key == "mode":
            st.session_state[key] = "rag"
        elif key == "upload_key":
            st.session_state[key] = 0


# ===================== 核心函数 =====================

def switch_kb(kb_name):
    st.session_state.kb_name = kb_name
    st.session_state.kb_ready = False
    st.session_state.kb_doc_count = 0
    clear_vector_store_cache()
    clear_embedding_cache()

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
    clear_vector_store_cache()
    clear_embedding_cache()

    docs_dir = get_documents_dir(kb)
    vec_dir = get_vector_store_dir(kb)

    documents = load_all_documents(docs_dir)
    if not documents:
        return False

    chunks = split_documents(documents)
    build_vector_store(chunks, vec_dir, overwrite=True)

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
    conv_id = create_conversation()
    st.session_state.conv_id = conv_id
    st.session_state.conv_title = "新对话"
    st.session_state.messages = []


def save_current_conv():
    if st.session_state.conv_id and st.session_state.messages:
        save_messages(st.session_state.conv_id, st.session_state.messages)


# ===================== 首次加载 =====================
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


# ===================== 页面 =====================
st.markdown('<div class="header"><h1>🧠 RAG 智能知识库</h1><p>👋 %s · 多知识库 · Agent 模式 · 联网搜索</p></div>' % (user.display_name or user.username), unsafe_allow_html=True)

current_kb = get_knowledge_base_info(st.session_state.kb_name) if st.session_state.kb_name else None
badge_style = "rgba(0,200,83,0.15);color:#00C853" if st.session_state.kb_ready else "rgba(255,152,0,0.15);color:#FF9800"
badge = f'<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;font-size:0.75rem;background:{badge_style};border:1px solid rgba(255,255,255,0.1);">● {"已就绪" if st.session_state.kb_ready else "未加载"}</span>'

st.markdown(f"""
<div style="display:flex;gap:1rem;margin-bottom:0.8rem;flex-wrap:wrap;align-items:center;">
    <div class="stat-card"><div class="num">{st.session_state.kb_doc_count}</div><div class="label">文档段</div></div>
    <div class="stat-card"><div class="num">{current_kb["doc_count"] if current_kb else 0}</div><div class="label">文件数</div></div>
    <div class="stat-card"><div class="num">{settings.LLM_PROVIDER.upper()}</div><div class="label">LLM</div></div>
    {badge}
</div>""", unsafe_allow_html=True)


# ===================== 侧边栏 =====================
with st.sidebar:
    st.markdown(f"**👤 {user.username}**")
    if st.button("🚪 退出登录", use_container_width=True):
        clear_auth()
        st.rerun()
    st.markdown("---")

    # --- 知识库管理 ---
    st.markdown("**📚 知识库**")
    kbs = list_knowledge_bases()
    for kb in kbs:
        active = kb["name"] == st.session_state.kb_name
        label = f"{'▸ ' if active else '  '}{kb['display_name']} ({kb['doc_count']}文件)"
        if st.button(label, key=f"kb_{kb['name']}", use_container_width=True):
            switch_kb(kb["name"])
            st.rerun()

    with st.popover("＋ 新建知识库"):
        new_name = st.text_input("标识符", placeholder="my-notes", help="字母/数字/下划线/中划线")
        new_display = st.text_input("显示名称", placeholder="我的知识库")
        new_desc = st.text_input("描述（可选）")
        if st.button("创建", use_container_width=True, type="primary"):
            safe = "".join(c for c in (new_name or "").strip() if c.isalnum() or c in "_-")
            if safe:
                if create_knowledge_base(safe, new_display or safe, new_desc or ""):
                    switch_kb(safe)
                    st.rerun()
                else:
                    st.error("创建失败（名称可能已存在）")
            else:
                st.error("请输入有效标识符")

    if current_kb and len(kbs) > 1:
        if st.button(f"🗑️ 删除 [{current_kb['display_name']}]", use_container_width=True):
            delete_knowledge_base(current_kb["name"])
            remaining = list_knowledge_bases()
            if remaining:
                switch_kb(remaining[0]["name"])
            st.rerun()

    st.markdown("---")

    # --- 对话管理 ---
    st.markdown("**💬 对话**")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        if st.button("＋ 新建对话", use_container_width=True):
            new_conversation()
            st.rerun()
    with col_b:
        if st.button("💾 保存", use_container_width=True):
            save_current_conv()
            st.toast("已保存", icon="✅")

    for c in list_conversations()[:8]:
        active = c["id"] == st.session_state.conv_id
        label = f"{'▸ ' if active else '  '}{c['title'][:16]}"
        cols = st.columns([4, 1])
        with cols[0]:
            if st.button(label, key=f"conv_{c['id']}", use_container_width=True):
                switch_conversation(c["id"])
                st.rerun()
        with cols[1]:
            if st.button("✕", key=f"del_conv_{c['id']}"):
                delete_conversation(c["id"])
                if c["id"] == st.session_state.conv_id:
                    remaining = list_conversations()
                    if remaining:
                        switch_conversation(remaining[0]["id"])
                    else:
                        new_conversation()
                st.rerun()

    # 导出
    if st.session_state.messages:
        st.markdown("**📤 导出**")
        md = export_markdown(st.session_state.conv_id)
        txt = export_text(st.session_state.conv_id)
        cc, dd = st.columns(2)
        with cc:
            if md:
                st.download_button("📝 MD", md, file_name=f"chat_{st.session_state.conv_id}.md", mime="text/markdown", use_container_width=True)
        with dd:
            if txt:
                st.download_button("📄 TXT", txt, file_name=f"chat_{st.session_state.conv_id}.txt", mime="text/plain", use_container_width=True)

    st.markdown("---")

    # --- 文档管理 ---
    kb = st.session_state.kb_name
    if kb:
        st.markdown(f"**📤 上传到 [{current_kb['display_name'] if current_kb else kb}]**")
        uploaded = st.file_uploader("选择文件", type=["pdf", "txt", "md", "docx"], accept_multiple_files=True, label_visibility="collapsed", key=f"fu_{st.session_state.upload_key}")
        if uploaded:
            for f in uploaded:
                save_uploaded_file(kb, f.name, f.getbuffer())
            st.session_state.upload_key += 1
            with st.spinner("正在建立索引..."):
                ok = rebuild_current_kb()
            if ok:
                st.success("✅ 上传完成，已建立索引")
            else:
                st.info("文件已保存，但没有可索引的内容")
            st.rerun()

        docs = get_documents(kb)
        if docs:
            st.markdown(f"**📂 文档 ({len(docs)}个)**")
            for doc in docs:
                cols = st.columns([3, 1])
                with cols[0]:
                    if st.button(f"📄 {doc['name']}", key=f"preview_{doc['name']}", use_container_width=True):
                        with st.expander(f"📖 {doc['name']}", expanded=True):
                            st.text(preview_document(kb, doc["name"])[:2000])
                with cols[1]:
                    if st.button("✕", key=f"del_{doc['name']}"):
                        delete_document(kb, doc["name"])
                        st.rerun()

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🔄 刷新索引", use_container_width=True, type="primary"):
                with st.spinner("重建索引中..."):
                    if rebuild_current_kb():
                        st.success("重建完成！")
                        st.rerun()
        with col_r2:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

    # --- 模式切换 ---
    st.markdown("---")
    st.markdown("**⚡ 模式**")
    mode_options = {"rag": "📚 RAG 模式", "agent": "🤖 Agent 模式"}
    current_mode = st.session_state.mode
    selected_mode = st.radio("模式", options=list(mode_options.keys()), format_func=lambda x: mode_options[x],
                              index=0 if current_mode == "rag" else 1, label_visibility="collapsed", horizontal=True)
    if selected_mode != st.session_state.mode:
        st.session_state.mode = selected_mode
        st.rerun()
    mode_desc = {"rag": "基于知识库文档回答问题", "agent": "AI 自动选择：知识库/联网搜索/计算器"}
    st.caption(mode_desc[st.session_state.mode])

    st.markdown("---")
    st.caption(f"v3.0 | KB: {st.session_state.kb_name} | {settings.OLLAMA_MODEL}")


# ===================== 主对话区 =====================
title = st.session_state.conv_title or "新对话"
kb_display = current_kb["display_name"] if current_kb else "未选择"
st.markdown(f"#### 💬 {title}  ·  `📚 {kb_display}`")

# 显示消息
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    if role == "user":
        st.markdown(f'<div class="chat-user">💬 {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-assistant">🤖 {content}</div>', unsafe_allow_html=True)
        if "sources" in msg and msg["sources"]:
            for s in msg["sources"]:
                src = s.get("source", "文档") if isinstance(s, dict) else "文档"
                txt = s.get("content", "") if isinstance(s, dict) else str(s)
                st.markdown(f'<div class="source-card"><span class="tag">📄 {src}</span>{txt}</div>', unsafe_allow_html=True)

# 输入框
if prompt := st.chat_input("输入你的问题..."):
    st.markdown(f'<div class="chat-user">💬 {prompt}</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            vec_dir = get_vector_store_dir(st.session_state.kb_name) if st.session_state.kb_name else None
            history = st.session_state.messages[:-1]
            mode = st.session_state.mode

            if mode == "rag" and st.session_state.kb_ready:
                # RAG 模式：流式回答
                full_response = ""
                for chunk in ask_stream(prompt, chat_history=history, vector_dir=vec_dir):
                    full_response += chunk
                    if "__SOURCES__:" in full_response:
                        break
                    placeholder.markdown(f'<div class="chat-assistant">🤖 {full_response}▌</div>', unsafe_allow_html=True)

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
                        st.markdown(f'<div class="source-card"><span class="tag">📄 {s.get("source", "文档")}</span>{s.get("content", "")}</div>', unsafe_allow_html=True)

                st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources_data})

            elif mode == "agent" or not st.session_state.kb_ready:
                # Agent 模式（或 KB 未就绪时的 RAG）
                with st.spinner("🤔 思考中..."):
                    if mode == "agent":
                        from agent_tools import ask_agent
                        from query import clean_deepseek_output
                        agent_result = ask_agent(prompt, vector_dir=vec_dir if st.session_state.kb_ready else None, chat_history=history)
                        answer = clean_deepseek_output(agent_result["answer"])
                        mode_tag = {"rag": "📚知识库", "web": "🌐联网", "direct": "💡直接回答"}.get(agent_result["mode"], "🤖Agent")
                        display = f"{answer}\n\n<sup style='color:rgba(255,255,255,0.3);font-size:0.7rem;'>回答方式: {mode_tag}</sup>"
                        placeholder.markdown(f'<div class="chat-assistant">🤖 {display}</div>', unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": answer + f"\n\n*({mode_tag})*"})
                    else:
                        # KB 未就绪，直接 LLM
                        from query import get_llm, clean_deepseek_output
                        llm = get_llm()
                        raw = llm.invoke(prompt).content
                        answer = clean_deepseek_output(raw)
                        placeholder.markdown(f'<div class="chat-assistant">🤖 {answer}</div>', unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": answer + "\n\n*(无知识库，AI 直接回答)*"})

            save_current_conv()

        except Exception as e:
            logger.error(f"问答出错: {e}", exc_info=True)
            st.error(f"出错了: {e}")
