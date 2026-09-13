"""
对话历史管理
保存、加载、导出聊天记录

安全约定:
    conv_id 会被拼进文件路径，而它来自 URL 路径参数，
    因此所有接收 conv_id 的函数都必须先过 validate_conv_id()。
    归属校验统一走 owner_id 参数：传 None 表示不校验（内部调用），
    传具体用户 id 时，不属于该用户的对话一律视为不存在。
"""

import os
import re
import json
import uuid
from datetime import datetime
from typing import List, Optional

# 对话存储目录
CONVERSATIONS_DIR = os.path.join(os.path.dirname(__file__), "conversations")
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

# 对话 ID 由 str(uuid.uuid4())[:8] 生成；这里允许的字符集不含 "." 与路径分隔符
_CONV_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_conv_id(conv_id: str) -> str:
    """校验对话 ID，合法则原样返回，否则抛 ValueError"""
    if not isinstance(conv_id, str) or not _CONV_ID_RE.match(conv_id):
        raise ValueError(f"非法对话 ID: {conv_id!r}")
    return conv_id


def _conversation_path(conv_id: str) -> str:
    return os.path.join(CONVERSATIONS_DIR, f"{validate_conv_id(conv_id)}.json")


def _read(conv_id: str) -> Optional[dict]:
    """读取对话原始数据，不存在或损坏返回 None"""
    path = _conversation_path(conv_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def _owned(data: Optional[dict], owner_id: Optional[str]) -> bool:
    """判断对话数据是否归 owner_id 所有（owner_id 为 None 时不校验）"""
    if data is None:
        return False
    if owner_id is None:
        return True
    return data.get("owner_id", "") == owner_id


def _all_conversations(owner_id: Optional[str] = None) -> List[dict]:
    """扫描所有对话文件（可按归属过滤）"""
    convs = []
    if not os.path.exists(CONVERSATIONS_DIR):
        return convs
    for f in sorted(os.listdir(CONVERSATIONS_DIR), reverse=True):
        if not f.endswith(".json"):
            continue
        conv_id = f[:-5]
        try:
            validate_conv_id(conv_id)
        except ValueError:
            continue
        data = _read(conv_id)
        if data is None or not _owned(data, owner_id):
            continue
        convs.append({
            "id": data.get("id", conv_id),
            "title": data.get("title", "新对话"),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "message_count": len(data.get("messages", [])),
        })
    return convs


def create_conversation(title: str = "新对话", owner_id: str = "") -> str:
    """创建新对话，返回对话 ID"""
    conv_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data = {
        "id": conv_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "owner_id": owner_id,
        "messages": [],
    }
    with open(_conversation_path(conv_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return conv_id


def load_conversation(conv_id: str, owner_id: Optional[str] = None) -> Optional[List[dict]]:
    """
    加载对话消息列表

    owner_id 传入时做归属校验，不属于该用户的对话返回 None（对调用方等同于"不存在"）。
    """
    data = _read(conv_id)
    if not _owned(data, owner_id):
        return None
    return data.get("messages", [])


def save_messages(conv_id: str, messages: List[dict], owner_id: str = ""):
    """保存消息到对话"""
    path = _conversation_path(conv_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        data = _read(conv_id)
        if data is None:
            data = {
                "id": conv_id, "title": "新对话", "created_at": now,
                "owner_id": owner_id, "messages": [],
            }
        elif owner_id and not data.get("owner_id"):
            # 老对话补上归属
            data["owner_id"] = owner_id

        data["messages"] = messages
        data["updated_at"] = now

        # 自动用第一条用户消息做标题
        if data["title"] == "新对话":
            for msg in messages:
                if msg["role"] == "user":
                    data["title"] = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
                    break

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[chat_history] 保存失败: {e}")


def delete_conversation(conv_id: str, owner_id: Optional[str] = None) -> bool:
    """
    删除对话

    返回是否真的删除了。owner_id 传入时不匹配则不动（返回 False）。
    """
    data = _read(conv_id)
    if not _owned(data, owner_id):
        return False
    os.remove(_conversation_path(conv_id))
    return True


def list_conversations(owner_id: Optional[str] = None) -> List[dict]:
    """列出对话（按更新时间倒序，可按归属过滤）"""
    convs = _all_conversations(owner_id)
    convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return convs


def export_markdown(conv_id: str, owner_id: Optional[str] = None) -> Optional[str]:
    """导出对话为 Markdown 格式"""
    messages = load_conversation(conv_id, owner_id)
    if not messages:
        return None

    data = _read(conv_id) or {}
    title = data.get("title", "对话记录")
    created = data.get("created_at", "")
    lines = [
        f"# {title}",
        f"",
        f"*创建时间: {created}*",
        f"",
        f"---",
        f"",
    ]
    for msg in messages:
        role = "👤 **用户**" if msg["role"] == "user" else "🤖 **AI**"
        content = msg.get("content", "")
        lines.append(f"### {role}")
        lines.append("")
        lines.append(content)
        lines.append("")

        sources = msg.get("sources", [])
        if sources:
            lines.append("**来源:**")
            for s in sources:
                src = s.get("source", "未知") if isinstance(s, dict) else s
                lines.append(f"- {src}")
            lines.append("")

    return "\n".join(lines)


def export_text(conv_id: str, owner_id: Optional[str] = None) -> Optional[str]:
    """导出对话为纯文本格式"""
    messages = load_conversation(conv_id, owner_id)
    if not messages:
        return None

    lines = []
    for msg in messages:
        role = "用户" if msg["role"] == "user" else "AI"
        content = msg.get("content", "")
        lines.append(f"[{role}]")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


def migrate_ownerless_conversations(owner_id: str) -> int:
    """
    把没有归属的对话划给指定用户（一次性历史数据迁移）

    返回被迁移的对话数量。
    """
    migrated = 0
    if not os.path.exists(CONVERSATIONS_DIR):
        return migrated
    for f in sorted(os.listdir(CONVERSATIONS_DIR)):
        if not f.endswith(".json"):
            continue
        conv_id = f[:-5]
        try:
            validate_conv_id(conv_id)
        except ValueError:
            continue
        data = _read(conv_id)
        if data is None or data.get("owner_id"):
            continue
        data["owner_id"] = owner_id
        try:
            with open(_conversation_path(conv_id), "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            migrated += 1
        except OSError:
            continue
    return migrated
