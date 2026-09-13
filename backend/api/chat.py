"""
对话 API: 聊天、对话历史管理

归属校验约定:
    所有对话读写都带 owner_id —— 此前 _require_user 只是"验证了但不用"，
    结果任何登录用户都能列出并删除所有人的聊天记录。
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.auth import validate_session
from app.logger import logger
from backend.api.knowledge_bases import get_owned_kb_or_404
from chat_history import (
    list_conversations, create_conversation, load_conversation,
    save_messages, delete_conversation, export_markdown, export_text,
)
from app.rag.engine import ask_stream
from agent_tools import ask_agent
from kb_manager import get_vector_store_dir

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


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)
    kb_name: str = ""
    mode: str = "rag"  # "rag" | "agent"
    conv_id: str = ""
    hybrid_search: bool = True


# ============ 对话管理 ============

@router.get("/conversations")
async def get_conversations(user_id: str = Depends(_require_user)):
    """获取当前用户的对话列表"""
    return {"data": list_conversations(owner_id=user_id) or []}


@router.post("/conversations")
async def new_conversation(user_id: str = Depends(_require_user)):
    """创建新对话"""
    conv_id = create_conversation(owner_id=user_id)
    return {"conv_id": conv_id, "title": "新对话"}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, user_id: str = Depends(_require_user)):
    """获取对话详情（非本人对话按不存在处理）"""
    try:
        msgs = load_conversation(conv_id, owner_id=user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法对话 ID")
    if msgs is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"data": {"id": conv_id, "messages": msgs}}


@router.delete("/conversations/{conv_id}")
async def remove_conversation(conv_id: str, user_id: str = Depends(_require_user)):
    """删除对话（仅限自己的）"""
    try:
        ok = delete_conversation(conv_id, owner_id=user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法对话 ID")
    if not ok:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"message": "删除成功"}


@router.get("/conversations/{conv_id}/export")
async def export_conversation(
    conv_id: str,
    fmt: str = Query("md"),
    user_id: str = Depends(_require_user),
):
    """导出对话"""
    try:
        if fmt == "md":
            content = export_markdown(conv_id, owner_id=user_id)
        else:
            content = export_text(conv_id, owner_id=user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法对话 ID")
    if content is None:
        raise HTTPException(status_code=404, detail="对话不存在或为空")
    return {"content": content}


# ============ 问答（流式 SSE） ============

@router.post("/ask")
async def ask_question(req: ChatRequest, user_id: str = Depends(_require_user)):
    """
    发送问题，流式返回 SSE 事件

    返回格式:
    event: token   data: 文本片段
    event: sources data: [{source, content}]
    event: done    data: ""
    """
    vector_dir = None
    if req.kb_name:
        # 越权闸门：不是自己的知识库直接 404，避免用别人的库作答
        get_owned_kb_or_404(req.kb_name, user_id)
        try:
            vector_dir = get_vector_store_dir(req.kb_name)
        except ValueError:
            raise HTTPException(status_code=400, detail="非法知识库名")

    conv_id = req.conv_id
    if conv_id:
        # 确认该对话属于当前用户，避免把消息写进别人的对话
        try:
            if load_conversation(conv_id, owner_id=user_id) is None:
                raise HTTPException(status_code=404, detail="对话不存在")
        except ValueError:
            raise HTTPException(status_code=400, detail="非法对话 ID")

    async def event_generator():
        full_answer = ""
        try:
            if req.mode == "rag" and req.kb_name:
                for chunk in ask_stream(req.question, vector_dir=vector_dir):
                    if "__SOURCES__:" in chunk:
                        parts = chunk.split("__SOURCES__:")
                        if parts[0]:
                            yield {"event": "token", "data": parts[0]}
                        if len(parts) > 1:
                            try:
                                sources = json.loads(parts[1])
                                yield {"event": "sources", "data": json.dumps(sources)}
                            except json.JSONDecodeError:
                                pass
                    else:
                        full_answer += chunk
                        yield {"event": "token", "data": chunk}
            else:
                # Agent 模式
                res = ask_agent(req.question, vector_dir=vector_dir)
                answer = res.get("answer", "")
                full_answer = answer
                yield {"event": "token", "data": answer}
                yield {"event": "mode", "data": res.get("mode", "direct")}

            # 保存对话（归属当前用户）
            if conv_id:
                msgs = load_conversation(conv_id, owner_id=user_id) or []
                msgs.append({"role": "user", "content": req.question})
                msgs.append({"role": "assistant", "content": full_answer})
                save_messages(conv_id, msgs, owner_id=user_id)

            yield {"event": "done", "data": ""}

        except Exception as e:
            logger.error(f"问答流式输出失败: {e}", exc_info=True)
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
