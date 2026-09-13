"""
对话 API: 聊天、对话历史管理
"""

import json
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.auth import validate_session
from chat_history import (
    list_conversations, create_conversation, load_conversation,
    save_messages, delete_conversation, export_markdown, export_text,
)
from app.rag.engine import ask_stream
from agent_tools import ask_agent
from kb_manager import get_vector_store_dir

router = APIRouter()


def _require_user(authorization: str = Header(...)):
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
async def get_conversations(authorization: str = Header(...)):
    """获取对话列表"""
    _require_user(authorization)
    convs = list_conversations()
    return {"data": convs or []}


@router.post("/conversations")
async def new_conversation(authorization: str = Header(...)):
    """创建新对话"""
    _require_user(authorization)
    conv_id = create_conversation()
    return {"conv_id": conv_id, "title": "新对话"}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, authorization: str = Header(...)):
    """获取对话详情"""
    _require_user(authorization)
    msgs = load_conversation(conv_id)
    return {"data": {"id": conv_id, "messages": msgs or []}}


@router.delete("/conversations/{conv_id}")
async def remove_conversation(conv_id: str, authorization: str = Header(...)):
    """删除对话"""
    _require_user(authorization)
    delete_conversation(conv_id)
    return {"message": "删除成功"}


@router.get("/conversations/{conv_id}/export")
async def export_conversation(
    conv_id: str,
    fmt: str = Query("md"),
    authorization: str = Header(...),
):
    """导出对话"""
    _require_user(authorization)
    if fmt == "md":
        content = export_markdown(conv_id)
    else:
        content = export_text(conv_id)
    return {"content": content or ""}


# ============ 问答（流式 SSE） ============

@router.post("/ask")
async def ask_question(req: ChatRequest, authorization: str = Header(...)):
    """
    发送问题，流式返回 SSE 事件

    返回格式:
    data: {"type": "token", "content": "..."}
    data: {"type": "sources", "content": [...]}
    data: {"type": "done"}
    """
    _require_user(authorization)

    vector_dir = get_vector_store_dir(req.kb_name) if req.kb_name else None

    async def event_generator():
        full_answer = ""
        try:
            if req.mode == "rag" and req.kb_name:
                # RAG 模式
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
                yield {"event": "token", "data": answer}
                yield {"event": "mode", "data": res.get("mode", "direct")}

            # 保存对话
            if req.conv_id:
                from chat_history import load_conversation, save_messages
                msgs = load_conversation(req.conv_id) or []
                msgs.append({"role": "user", "content": req.question})
                msgs.append({"role": "assistant", "content": full_answer})
                save_messages(req.conv_id, msgs)

            yield {"event": "done", "data": ""}

        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
