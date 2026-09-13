"""
知识库 API: 列表、创建、删除

归属校验约定（重要）:
    _require_user 返回的 user_id 必须真正用于过滤和校验，
    绝不能"验证了但不用"——那正是此前越权访问的成因：
    任何登录用户都能看到、删除他人的知识库。
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.auth import validate_session
from kb_manager import (
    list_knowledge_bases, create_knowledge_base, delete_knowledge_base,
    get_knowledge_base_info,
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


def get_owned_kb_or_404(name: str, user_id: str) -> dict:
    """
    取知识库信息并确认归属

    "不存在"和"不属于你"统一返回 404：区分开来会泄露
    "某个名字的知识库确实存在"这一信息。
    """
    try:
        info = get_knowledge_base_info(name)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法知识库名")
    if not info or info.get("owner_id") != user_id:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return info


class CreateKBRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field("", max_length=128)
    description: str = ""


@router.get("/")
async def list_kbs(user_id: str = Depends(_require_user)):
    """获取当前用户的知识库列表"""
    return {"data": list_knowledge_bases(owner_id=user_id) or []}


@router.get("/{name}")
async def get_kb(name: str, user_id: str = Depends(_require_user)):
    """获取单个知识库信息"""
    return {"data": get_owned_kb_or_404(name, user_id)}


@router.post("/")
async def create_kb(req: CreateKBRequest, user_id: str = Depends(_require_user)):
    """创建知识库（归属为当前用户）"""
    ok = create_knowledge_base(
        req.name, req.display_name or req.name, req.description, owner_id=user_id,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="知识库创建失败（可能已存在）")
    return {"message": "创建成功", "name": req.name}


@router.delete("/{name}")
async def delete_kb(name: str, user_id: str = Depends(_require_user)):
    """删除知识库（仅限自己拥有的）"""
    get_owned_kb_or_404(name, user_id)
    delete_knowledge_base(name)
    return {"message": "删除成功"}
