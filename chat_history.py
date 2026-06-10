"""
对话历史管理
保存、加载、导出聊天记录
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Optional

# 对话存储目录
CONVERSATIONS_DIR = os.path.join(os.path.dirname(__file__), "conversations")
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)


def _conversation_path(conv_id: str) -> str:
    return os.path.join(CONVERSATIONS_DIR, f"{conv_id}.json")


def _all_conversations() -> List[dict]:
    """扫描所有对话文件"""
    convs = []
    if not os.path.exists(CONVERSATIONS_DIR):
        return convs
    for f in sorted(os.listdir(CONVERSATIONS_DIR), reverse=True):
        if f.endswith(".json"):
            try:
                with open(os.path.join(CONVERSATIONS_DIR, f), "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    convs.append({
                        "id": data["id"],
                        "title": data.get("title", "新对话"),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": len(data.get("messages", [])),
                    })
            except (json.JSONDecodeError, KeyError):
                continue
    return convs


def create_conversation(title: str = "新对话") -> str:
    """创建新对话，返回对话 ID"""
    conv_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data = {
        "id": conv_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    with open(_conversation_path(conv_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return conv_id


def load_conversation(conv_id: str) -> Optional[List[dict]]:
    """加载对话消息列表"""
    path = _conversation_path(conv_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def save_messages(conv_id: str, messages: List[dict]):
    """保存消息到对话"""
    path = _conversation_path(conv_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"id": conv_id, "title": "新对话", "created_at": now, "messages": []}

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


def delete_conversation(conv_id: str):
    """删除对话"""
    path = _conversation_path(conv_id)
    if os.path.exists(path):
        os.remove(path)


def list_conversations() -> List[dict]:
    """列出所有对话（按更新时间倒序）"""
    convs = _all_conversations()
    convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return convs


def export_markdown(conv_id: str) -> Optional[str]:
    """导出对话为 Markdown 格式"""
    messages = load_conversation(conv_id)
    if not messages:
        return None

    path = _conversation_path(conv_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

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


def export_text(conv_id: str) -> Optional[str]:
    """导出对话为纯文本格式"""
    messages = load_conversation(conv_id)
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
