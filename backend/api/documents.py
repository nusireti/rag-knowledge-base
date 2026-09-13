"""
文档 API: 上传、列表、删除、预览

两处约定:
1. 归属校验 —— 每个接口都先确认 kb_name 属于当前用户，否则 404
2. 路径校验 —— kb_name / filename 全部来自 Query 参数，
   拼路径的函数（kb_manager）会先做校验，校验失败转成 400
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.auth import validate_session
from app.logger import logger
from backend.api.knowledge_bases import get_owned_kb_or_404
from kb_manager import (
    get_documents, delete_document, save_uploaded_file,
    preview_document,
    get_documents_dir, get_vector_store_dir,
)

router = APIRouter()


def _require_user(authorization: str = Header("")) -> str:
    """从 Authorization header 解析用户，返回 user_id"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    user_id = validate_session(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return user_id


def _rebuild_kb_index(kb_name: str):
    """
    全量重建知识库索引（同步、耗时）

    返回切块数；没有可索引文档或失败时返回 None。
    调用方必须用 run_in_threadpool 包起来 —— 这是纯 CPU/IO 的同步活，
    直接在 async 处理函数里跑会阻塞整个事件循环，期间所有请求一起卡住。
    """
    from app.rag.ingest import (
        load_all_documents, split_documents, build_vector_store, clear_index,
    )

    try:
        docs_dir = get_documents_dir(kb_name)
        vec_dir = get_vector_store_dir(kb_name)
        documents = load_all_documents(docs_dir)
        if not documents:
            # 文档全删光了，向量库也要一并清空，
            # 否则库里还留着已删文档的切块，问什么都能答出来。
            clear_index(vec_dir)
            return None
        chunks = split_documents(documents)
        build_vector_store(chunks, vec_dir, overwrite=True)
        return len(chunks)
    except Exception as e:
        logger.warning(f"索引重建失败 [{kb_name}]: {e}")
        return None


@router.get("/")
async def list_docs(kb_name: str = Query(...), user_id: str = Depends(_require_user)):
    """获取知识库的文档列表"""
    get_owned_kb_or_404(kb_name, user_id)
    try:
        docs = get_documents(kb_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": docs or []}


@router.post("/upload")
async def upload_doc(
    kb_name: str = Query(...),
    file: UploadFile = File(...),
    user_id: str = Depends(_require_user),
):
    """上传文档到知识库（自动增量索引）"""
    get_owned_kb_or_404(kb_name, user_id)
    try:
        data = await file.read()
        stored_path, _safe_name = save_uploaded_file(kb_name, file.filename or "untitled", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")

    # 上传完必须把文件索引进向量库，否则文档只是躺在磁盘上、搜不到。
    # Streamlit 版是在 UI 层调 rebuild 的，走 API 的 React 版原先缺了这一步 ——
    # 表现就是"上传成功、但问什么都说文档中没有相关信息"。
    from app.rag.ingest import index_single_file

    chunks = await run_in_threadpool(index_single_file, get_vector_store_dir(kb_name), stored_path)
    if chunks < 0:
        return {
            "message": "上传成功，但索引失败，请手动重建索引",
            "filename": file.filename,
            "indexed": 0,
        }
    return {"message": "上传成功", "filename": file.filename, "indexed": chunks}


@router.post("/rebuild")
async def rebuild_index(kb_name: str = Query(...), user_id: str = Depends(_require_user)):
    """重建知识库索引"""
    get_owned_kb_or_404(kb_name, user_id)
    chunks = await run_in_threadpool(_rebuild_kb_index, kb_name)
    if chunks is None:
        raise HTTPException(status_code=400, detail="没有可索引的文档，或索引失败")
    return {"message": "索引重建完成", "chunks": chunks}


@router.delete("/")
async def delete_doc(
    kb_name: str = Query(...),
    filename: str = Query(...),
    user_id: str = Depends(_require_user),
):
    """删除文档（同时删除其向量块）"""
    from app.rag.ingest import remove_document_chunks

    get_owned_kb_or_404(kb_name, user_id)
    try:
        delete_document(kb_name, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 只删文件不够：向量块还在库里，已删除的文档照样会被检索出来。
    vec_dir = get_vector_store_dir(kb_name)
    removed = await run_in_threadpool(remove_document_chunks, vec_dir, filename)
    if removed <= 0:
        # 没匹配上（索引是旧格式，或该文件本就没进过索引）→ 全量重建兜底
        await run_in_threadpool(_rebuild_kb_index, kb_name)
    return {"message": "删除成功"}


@router.get("/preview")
async def preview_doc(
    kb_name: str = Query(...),
    filename: str = Query(...),
    max_chars: int = Query(1500, ge=1, le=20000),
    user_id: str = Depends(_require_user),
):
    """预览文档内容"""
    get_owned_kb_or_404(kb_name, user_id)
    try:
        content = preview_document(kb_name, filename, max_chars)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"content": content}
