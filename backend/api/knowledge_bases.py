"""
知识库 API: 列表、创建、删除
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from app.auth import validate_session
from kb_manager import (
    list_knowledge_bases, create_knowledge_base, delete_knowledge_base,
    get_knowledge_base_info,
)

router = APIRouter()


def _require_user(authorization: str = Header(...)):
    """从 Authorization header 解析用户"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    user_id = validate_session(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return user_id


class CreateKBRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field("", max_length=128)
    description: str = ""


@router.get("/")
async def list_kbs(authorization: str = Header(...)):
    """获取所有知识库"""
    _require_user(authorization)
    return {"data": list_knowledge_bases() or []}


@router.get("/{name}")
async def get_kb(name: str, authorization: str = Header(...)):
    """获取单个知识库信息"""
    _require_user(authorization)
    kb = get_knowledge_base_info(name)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return {"data": kb}


@router.post("/")
async def create_kb(req: CreateKBRequest, authorization: str = Header(...)):
    """创建知识库"""
    _require_user(authorization)
    ok = create_knowledge_base(req.name, req.display_name or req.name, req.description)
    if not ok:
        raise HTTPException(status_code=409, detail="知识库创建失败（可能已存在）")
    return {"message": "创建成功", "name": req.name}


@router.delete("/{name}")
async def delete_kb(name: str, authorization: str = Header(...)):
    """删除知识库"""
    _require_user(authorization)
    delete_knowledge_base(name)
    return {"message": "删除成功"}
