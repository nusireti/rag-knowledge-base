"""
RAG 知识库 - FastAPI 后端入口
启动: uvicorn backend.main:app --reload --port 8000
"""

import os, sys
from pathlib import Path

# 把项目根目录加入路径，让 backend/ 能引用 app/ 下的代码
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
if str(_root.parent) not in sys.path:
    sys.path.insert(0, str(_root.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.api import auth, knowledge_bases, documents, chat, models

app = FastAPI(
    title="RAG 智能知识库 API",
    version="4.0",
    description="企业级 RAG 知识库后端 API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ---- 安全中间件 ----
# CORS: 仅允许本地前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 开发服务器
        "http://localhost:3000",  # 备用
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---- 路由注册 ----
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(knowledge_bases.router, prefix="/api/knowledge-bases", tags=["知识库"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档"])
app.include_router(chat.router, prefix="/api/chat", tags=["对话"])
app.include_router(models.router, prefix="/api/models", tags=["模型"])


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "4.0"}
