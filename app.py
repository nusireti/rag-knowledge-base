"""
RAG 智能知识库 - 启动入口
v4.0 新版入口已迁移至 app/web/ui.py
运行: python run.py web
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(page_title="RAG 智能知识库", page_icon="🦝", layout="wide")

st.markdown("""
<style>
    .stApp { background: #0A0A12; display: flex; justify-content: center; align-items: center; }
    .redirect-card {
        max-width: 480px; margin: 120px auto; padding: 3rem;
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
        border-radius: 20px; text-align: center;
    }
    h1 { color: #E8E8F0; font-size: 2rem; margin-bottom: 1rem; }
    p { color: rgba(255,255,255,0.4); line-height: 1.8; }
    .cmd {
        background: rgba(124,92,252,0.1); border: 1px solid rgba(124,92,252,0.2);
        padding: 0.6rem 1.2rem; border-radius: 10px; font-family: monospace;
        color: #9D8BFF; margin: 1rem 0; display: inline-block;
    }
</style>
<div class="redirect-card">
    <h1>🦝 RAG v4.0</h1>
    <p>新版入口已迁移</p>
    <div class="cmd">python run.py web</div>
    <p style="font-size:0.85rem;">或直接访问<br>app/web/ui.py</p>
</div>
""", unsafe_allow_html=True)

st.stop()
