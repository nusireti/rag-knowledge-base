"""RAG 知识库 - 高级版 Web 界面
v3.0: Agent 工具调用 + 联网搜索"""

import os
import json
import streamlit as st

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

st.set_page_config(page_title="RAG 智能知识库", page_icon="🧠", layout="wide")

from ingest import load_documents, split_documents, get_embedding_model, clear_embedding_cache
from query import create_qa_chain, clear_cache, ask_stream
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
from config import EMBEDDING_PROVIDER, LLM_PROVIDER, OLLAMA_MODEL, OPENAI_LLM_MODEL


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
    .header h1 { color: white; font-weight: 700; font-size: 1.4rem; margin: 0; }
    .header p { color: rgba(255,255,255,0.85); margin: 0.2rem 0 0 0; font-size: 0.85rem; }
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
        margin-left: auto; margin-bottom: 0.8rem;
        box-shadow: 0 4px 12px rgba(108,92,231,0.2);
        font-size: 0.95rem;
    }
    .chat-assistant {
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
        padding: 0.7rem 1.1rem; border-radius: 18px 18px 18px 4px;
        max-width: 92%; margin-right: auto; margin-bottom: 0.8rem;
        line-height: 1.6; font-size: 0.95rem;
    }
    .source-card {
        background: rgba(108,92,231,0.08); border: 1px solid rgba(108,92,231,0.15);
        border-radius: 8px; padding: 0.4rem 0.7rem; margin: 0.2rem 0; font-size: 0.75rem;
    }
    .source-card .tag {
        background: rgba(108,92,231,0.2); color: #a29bfe;
        padding: 1px 8px; border-radius: 10px; font-size: 0.65rem; margin-right: 6px;
    }
    .kb-item {
        padding: 0.45rem 0.6rem; border-radius: 8px; cursor: pointer;
        font-size: 0.85rem; margin: 0.1rem 0;
        transition: all 0.15s; border-left: 3px solid transparent;
    }
    .kb-item:hover { background: rgba(108,92,231,0.1); }
    .kb-item.active { background: rgba(108,92,231,0.18); border-left-color: #6C5CE7; }
    section[data-testid="stSidebar"] { background: rgba(15,15,26,0.95) !important; border-right: 1px solid rgba(255,255,255,0.06); }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    div[data-testid="stChatInput"] {
        background: rgba(255,255,255,0.18) !important; border-radius: 24px !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #FFFFFF !important; font-size: 1rem !important; caret-color: #6C5CE7 !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder { color: rgba(255,255,255,0.8) !important; }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #6C5CE7 !important; box-shadow: 0 0 0 3px rgba(108,92,231,0.25) !important;
    }
</style>
""", unsafe_allow_html=True)


# ===================== 初始化状态 =====================
defaults = {
    "messages": [],
    "conv_id": None,
    "conv_title": "新对话",
    "kb_name": None,
    "kb_ready": False,
    "kb_doc_count": 0,
    "mode": "rag",  # "rag" | "agent"
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def get_current_kb_info():
    """获取当前知识库信息"""
    kb = st.session_state.kb_name
    if not kb:
        return None
    return get_knowledge_base_info(kb)


def switch_kb(kb_name: str):
    """切换知识库"""
    st.session_state.kb_name = kb_name
    st.session_state.kb_ready = False
    st.session_state.kb_doc_count = 0
    clear_cache()
    clear_embedding_cache()

    # 检查是否已建向量库
    vec_dir = get_vector_store_dir(kb_name)
    if os.path.exists(vec_dir) and any(os.scandir(vec_dir)):
        try:
            st.session_state.kb_ready = True
            docs = load_documents(get_documents_dir(kb_name))
            st.session_state.kb_doc_count = len(docs) if docs else 0
        except Exception:
            pass


def rebuild_current_kb():
    """重建当前知识库"""
    kb = st.session_state.kb_name
    if not kb:
        return False
    clear_cache()
    clear_embedding_cache()

    docs_dir = get_documents_dir(kb)
    vec_dir = get_vector_store_dir(kb)

    documents = load_documents(docs_dir)
    if not documents:
        return False

    chunks = split_documents(documents)
    embedding_model = get_embedding_model()

    # 重建向量库
    import shutil
    from pathlib import Path
    if Path(vec_dir).exists():
        shutil.rmtree(vec_dir)

    from langchain_chroma import Chroma
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=vec_dir,
    )

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
# 初始化知识库
if st.session_state.kb_name is None:
    kbs = list_knowledge_bases()
    if kbs:
        switch_kb(kbs[0]["name"])
    else:
        create_knowledge_base("default", "默认知识库", "默认知识库")
        switch_kb("default")

# 初始化对话
if st.session_state.conv_id is None:
    convs = list_conversations()
    if convs:
        switch_conversation(convs[0]["id"])
    else:
        new_conversation()


# ===================== 页面 =====================
st.markdown('<div class="header"><h1>🧠 RAG 智能知识库</h1><p>多知识库 · 对话自动保存 · 文档预览</p></div>', unsafe_allow_html=True)

# 状态栏
current_kb = get_current_kb_info()
kb_badge = f'● {current_kb["display_name"]}' if current_kb else "● 未选择"
badge_color = "rgba(0,200,83,0.15);color:#00C853" if st.session_state.kb_ready else "rgba(255,152,0,0.15);color:#FF9800"
badge = f'<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;font-size:0.75rem;background:{badge_color};border:1px solid rgba(255,255,255,0.1);">{kb_badge}</span>'

st.markdown(f"""
<div style="display:flex;gap:1rem;margin-bottom:0.8rem;flex-wrap:wrap;align-items:center;">
    <div class="stat-card"><div class="num">{st.session_state.kb_doc_count}</div><div class="label">文档段</div></div>
    <div class="stat-card"><div class="num">{current_kb["doc_count"] if current_kb else 0}</div><div class="label">文件数</div></div>
    <div class="stat-card"><div class="num">{LLM_PROVIDER.upper()}</div><div class="label">LLM</div></div>
    {badge}
</div>
""", unsafe_allow_html=True)


# ===================== 侧边栏 =====================
with st.sidebar:
    st.markdown("#### ⚙️ 管理面板")

    # --- 知识库管理 ---
    st.markdown("**📚 知识库**")

    kbs = list_knowledge_bases()
    for kb in kbs:
        active = kb["name"] == st.session_state.kb_name
        label = f"{'▸ ' if active else '  '}{kb['display_name']} ({kb['doc_count']}文件)"
        if st.button(label, key=f"kb_{kb['name']}", use_container_width=True):
            switch_kb(kb["name"])
            st.rerun()

    # 新建知识库
    with st.popover("＋ 新建知识库", help="创建一个新的独立知识库"):
        new_name = st.text_input("标识符", placeholder="如: my-notes", help="字母/数字/下划线/中划线", key="new_kb_name")
        new_display = st.text_input("显示名称", placeholder="如: 我的笔记", help="可读的名称", key="new_kb_display")
        new_desc = st.text_input("描述（可选）", placeholder="这个知识库用来做什么", key="new_kb_desc")
        if st.button("创建知识库", use_container_width=True, type="primary"):
            safe_name = "".join(c for c in new_name.strip() if c.isalnum() or c in "_-") if new_name else ""
            if safe_name:
                if create_knowledge_base(safe_name, new_display or safe_name, new_desc or ""):
                    st.success(f"✅ 知识库 [{new_display or safe_name}] 已创建！")
                    switch_kb(safe_name)
                    st.rerun()
                else:
                    st.error("创建失败（名称可能已存在）")
            else:
                st.error("请输入有效的标识符（字母/数字/下划线）")

    # 删除当前知识库
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
        if st.button("＋ 新建", use_container_width=True):
            new_conversation()
            st.rerun()
    with col_b:
        if st.button("💾 保存", use_container_width=True):
            save_current_conv()
            st.toast("已保存", icon="✅")

    for c in list_conversations()[:8]:
        active = c["id"] == st.session_state.conv_id
        label = f"{'▸ ' if active else '  '}{c['title'][:16]}"
        if st.button(label, key=f"conv_{c['id']}", use_container_width=True):
            switch_conversation(c["id"])
            st.rerun()

    # 导出
    if st.session_state.messages:
        st.markdown("**📤 导出**")
        md = export_markdown(st.session_state.conv_id)
        txt = export_text(st.session_state.conv_id)
        cc, dd = st.columns(2)
        with cc:
            if md:
                st.download_button("📝 MD", data=md, file_name=f"对话_{st.session_state.conv_id}.md", mime="text/markdown", use_container_width=True)
        with dd:
            if txt:
                st.download_button("📄 TXT", data=txt, file_name=f"对话_{st.session_state.conv_id}.txt", mime="text/plain", use_container_width=True)

    st.markdown("---")

    # --- 文档上传 + 刷新 ---
    kb = st.session_state.kb_name
    if kb:
        st.markdown(f"**📤 上传到 [{current_kb['display_name'] if current_kb else kb}]**")

        # 用动态 key 防止上传后无限循环
        if "upload_key" not in st.session_state:
            st.session_state.upload_key = 0

        uploaded = st.file_uploader(
            "选择文件", type=["pdf", "txt", "md", "docx"],
            accept_multiple_files=True, label_visibility="collapsed",
            key=f"upload_{st.session_state.upload_key}",
        )

        if uploaded:
            saved = 0
            for f in uploaded:
                save_uploaded_file(kb, f.name, f.getbuffer())
                saved += 1

            # 递增 key 清空 uploader 状态，防止重复触发
            st.session_state.upload_key += 1

            # 自动重建知识库
            with st.spinner(f"已保存 {saved} 个文件，正在建立索引..."):
                ok = rebuild_current_kb()
            if ok:
                st.success(f"✅ 已保存 {saved} 个文件并建立索引，现在可以提问了！")
            else:
                st.info(f"已保存 {saved} 个文件，但没有可索引的文档内容")
            st.rerun()

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🔄 刷新知识库", use_container_width=True, type="primary"):
                with st.spinner("处理中..."):
                    if rebuild_current_kb():
                        st.toast("知识库已重建！", icon="🎉")
                        st.rerun()
        with col_r2:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                save_current_conv()
                st.rerun()

        # 文档列表 + 预览
        docs = get_documents(kb)
        if docs:
            st.markdown(f"**📂 文档 ({len(docs)}个)**")
            for doc in docs:
                cols = st.columns([3, 1, 1])
                with cols[0]:
                    preview_btn = st.button(f"📄 {doc['name']}", key=f"preview_{doc['name']}", help="点击预览", use_container_width=True)
                with cols[1]:
                    st.markdown(f'<div style="font-size:0.7rem;color:rgba(255,255,255,0.4);padding:6px 0;">{doc["size_str"]}</div>', unsafe_allow_html=True)
                with cols[2]:
                    if st.button("✕", key=f"del_{doc['name']}", help=f"删除 {doc['name']}"):
                        delete_document(kb, doc["name"])
                        st.rerun()

                if preview_btn:
                    with st.expander(f"📖 {doc['name']}", expanded=True):
                        content = preview_document(kb, doc["name"])
                        st.text(content[:2000])

    # --- 模式切换 ---
    st.markdown("---")
    st.markdown("**⚡ 模式**")
    current_mode = st.session_state.mode
    mode_options = {"rag": "📚 RAG 模式", "agent": "🤖 Agent 模式"}
    selected_mode = st.radio(
        "模式",
        options=list(mode_options.keys()),
        format_func=lambda x: mode_options[x],
        index=0 if current_mode == "rag" else 1,
        label_visibility="collapsed",
        horizontal=True,
    )
    if selected_mode != st.session_state.mode:
        st.session_state.mode = selected_mode
        st.rerun()

    mode_desc = {
        "rag": "基于知识库文档回答问题，流式输出",
        "agent": "AI 自动选择工具：知识库/联网搜索/计算器",
    }
    st.caption(mode_desc[st.session_state.mode])

    # 底部
    st.markdown("---")
    with st.expander("⚡ 高级"):
        if st.button("🧹 重置所有", use_container_width=True):
            import shutil
            for kb_ in list_knowledge_bases():
                vd = get_vector_store_dir(kb_["name"])
                if os.path.exists(vd):
                    shutil.rmtree(vd)
            clear_cache()
            clear_embedding_cache()
            st.session_state.kb_ready = False
            st.session_state.kb_doc_count = 0
            st.toast("已重置所有向量库", icon="🧹")
            st.rerun()

    st.caption(f"v3.0 | KB: {st.session_state.kb_name} | {'📚RAG' if st.session_state.mode=='rag' else '🤖Agent'}")


# ===================== 主对话区 =====================
title = st.session_state.conv_title or "新对话"
kb_name = current_kb["display_name"] if current_kb else "未选择知识库"
st.markdown(f"#### 💬 {title}  ·  `📚 {kb_name}`")

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
                st.markdown(f'<div class="source-card"><span class="tag">📄 {src_label}</span>{src_content}</div>', unsafe_allow_html=True)

# 输入框始终显示（不管知识库是否就绪）
input_disabled = False
input_placeholder = "输入你的问题..."
if not st.session_state.kb_ready and st.session_state.mode == "rag":
    input_disabled = False
    input_placeholder = "知识库尚未加载，但我仍然可以和你聊天（切换到 Agent 模式可联网搜索）..."

if prompt := st.chat_input(input_placeholder, disabled=input_disabled):
    st.markdown(f'<div class="chat-user">💬 {prompt}</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            vec_dir = get_vector_store_dir(st.session_state.kb_name) if st.session_state.kb_name else None
            history = st.session_state.messages[:-1]
            mode = st.session_state.mode

            if mode == "rag" and st.session_state.kb_ready:
                # === RAG 模式：流式输出 ===
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

                import re
                # 安全过滤：移除任何残留的 <think> 标签
                answer_clean = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
                placeholder.markdown(f'<div class="chat-assistant">🤖 {answer_clean}</div>', unsafe_allow_html=True)
                if sources_data:
                    for s in sources_data:
                        st.markdown(f'<div class="source-card"><span class="tag">📄 {s.get("source", "文档")}</span>{s.get("content", "")}</div>', unsafe_allow_html=True)

                st.session_state.messages.append({
                    "role": "assistant", "content": answer_clean, "sources": sources_data,
                })

            elif mode == "agent" or not st.session_state.kb_ready:
                # === Agent 模式（或 RAG 模式但 KB 未就绪）：直接用 LLM 回答 ===
                with st.spinner("🤔 思考中..."):
                    if mode == "agent":
                        agent_result = ask_agent(prompt, vector_dir=vec_dir if st.session_state.kb_ready else None, chat_history=history)
                        from query import clean_deepseek_output
                        answer = clean_deepseek_output(agent_result["answer"])
                        mode_tag = {"rag": "📚知识库", "web": "🌐联网", "direct": "💡直接回答"}.get(agent_result["mode"], "🤖Agent")
                        display = f"{answer}\n\n---\n<sup style='color:rgba(255,255,255,0.3);font-size:0.7rem;'>回答方式: {mode_tag}</sup>"
                        placeholder.markdown(f'<div class="chat-assistant">🤖 {display}</div>', unsafe_allow_html=True)
                        st.session_state.messages.append({
                            "role": "assistant", "content": answer + f"\n\n*(回答方式: {mode_tag})*",
                        })
                    else:
                        # RAG 模式但 KB 未就绪：直接让 LLM 回答
                        from query import get_llm, clean_deepseek_output
                        llm = get_llm()
                        answer = llm.invoke(prompt).content
                        answer_clean = clean_deepseek_output(answer)
                        placeholder.markdown(f'<div class="chat-assistant">🤖 {answer_clean}</div>', unsafe_allow_html=True)
                        st.session_state.messages.append({
                            "role": "assistant", "content": answer_clean + "\n\n*(无知识库，AI 基于自身知识回答)*",
                        })

            save_current_conv()

        except Exception as e:
            st.error(f"出错了: {e}")
