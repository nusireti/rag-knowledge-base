"""
知识库管理
支持多个知识库的创建、切换、删除
每个知识库有独立的文档目录和向量数据库

安全约定（重要）:
    凡是拿用户输入的 kb_name / filename 去拼路径的函数，
    必须统一走 validate_kb_name() 和 safe_doc_path()。
    直接 os.path.join 会让 kb_name="../../" 删掉项目外的目录。
"""

import os
import re
import json
import secrets
import shutil
from pathlib import Path
from typing import List, Optional

from app.logger import logger

# 知识库存储根目录
KB_ROOT = os.path.join(os.path.dirname(__file__), "knowledge_bases")
os.makedirs(KB_ROOT, exist_ok=True)

# 知识库名允许的字符集，与 create_knowledge_base 的清洗规则保持一致
_KB_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# 上传白名单
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


# ===================== 安全校验 =====================

def validate_kb_name(kb_name: str) -> str:
    """
    校验知识库名，合法则原样返回，否则抛 ValueError。

    拼路径前必须先过这里：kb_name 允许的字符集里不含 "." 和路径分隔符，
    因此 "../../etc" 这类输入会被直接拒绝。
    """
    if not isinstance(kb_name, str) or not _KB_NAME_RE.match(kb_name):
        raise ValueError(f"非法知识库名: {kb_name!r}")
    return kb_name


def safe_doc_path(kb_name: str, filename: str) -> str:
    """
    安全拼接"知识库文档目录 + 文件名"，返回绝对路径。

    两步防护：
    1. 只取 filename 的最后一段，丢掉一切目录成分
       （'..\\..\\x'、'../../x'、'C:\\Windows\\x' 都会被剥成 'x'）
    2. 再确认拼接结果仍落在文档目录内
    """
    validate_kb_name(kb_name)
    docs_dir = os.path.abspath(_kb_docs_path(kb_name))

    name = os.path.basename(str(filename).replace("\\", "/"))
    if not name or name.startswith("."):
        raise ValueError(f"非法文件名: {filename!r}")

    full = os.path.abspath(os.path.join(docs_dir, name))
    if not full.startswith(docs_dir + os.sep):
        raise ValueError(f"路径越界: {filename!r}")
    return full


# ===================== 路径 =====================

def _kb_path(kb_name: str) -> str:
    return os.path.join(KB_ROOT, validate_kb_name(kb_name))


def _kb_config_path(kb_name: str) -> str:
    return os.path.join(_kb_path(kb_name), "config.json")


def _kb_docs_path(kb_name: str) -> str:
    return os.path.join(KB_ROOT, kb_name, "documents")


def _kb_vector_path(kb_name: str) -> str:
    return os.path.join(KB_ROOT, kb_name, "vector_store")


# ===================== 查询 =====================

def list_knowledge_bases(owner_id: Optional[str] = None) -> List[dict]:
    """
    列出知识库

    参数:
        owner_id: 传入时只返回该用户拥有的知识库；
                  None 表示不筛归属（仅供内部/迁移逻辑使用）。
    """
    kbs = []
    if not os.path.exists(KB_ROOT):
        return kbs
    for name in sorted(os.listdir(KB_ROOT)):
        # 目录名来自磁盘，仍要过一遍校验：
        # 非法名字（例如手工建的怪目录）直接跳过，不要让整个列表炸掉
        try:
            validate_kb_name(name)
        except ValueError:
            continue
        info = get_knowledge_base_info(name)
        if info is None:
            continue
        if owner_id is not None and info.get("owner_id") != owner_id:
            continue
        kbs.append(info)
    return kbs


def get_knowledge_base_info(kb_name: str) -> Optional[dict]:
    """获取知识库信息，不存在返回 None"""
    config_path = _kb_config_path(kb_name)
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        config = {}

    docs_dir = _kb_docs_path(kb_name)
    doc_count = 0
    if os.path.exists(docs_dir):
        doc_count = len([f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))])

    vector_dir = _kb_vector_path(kb_name)
    has_vector = os.path.exists(vector_dir) and len(os.listdir(vector_dir)) > 0

    return {
        "name": kb_name,
        "display_name": config.get("display_name", kb_name),
        "description": config.get("description", ""),
        "doc_count": doc_count,
        "has_vector": has_vector,
        "created_at": config.get("created_at", ""),
        "owner_id": config.get("owner_id", ""),
    }


def kb_belongs_to(kb_name: str, owner_id: str) -> bool:
    """
    判断知识库是否属于指定用户。

    调用方必须用返回值做判断，不要"验证了但不用"——
    这正是 backend 此前的越权成因。
    """
    try:
        info = get_knowledge_base_info(kb_name)
    except ValueError:
        return False
    if not info:
        return False
    return info.get("owner_id") == owner_id


# ===================== 增删 =====================

def create_knowledge_base(
    name: str,
    display_name: str = "",
    description: str = "",
    owner_id: str = "",
) -> bool:
    """创建新知识库"""
    if not name or not name.strip():
        return False
    # 只允许字母、数字、下划线、中划线
    safe_name = "".join(c for c in name.strip() if c.isalnum() or c in "_-")
    if not safe_name:
        return False

    path = _kb_path(safe_name)
    if os.path.exists(path):
        return False  # 已存在

    os.makedirs(_kb_docs_path(safe_name), exist_ok=True)

    import datetime
    config = {
        "display_name": display_name or safe_name,
        "description": description or "",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "owner_id": owner_id,
    }
    with open(_kb_config_path(safe_name), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return True


def delete_knowledge_base(kb_name: str) -> bool:
    """删除知识库（kb_name 必须已通过 validate_kb_name）"""
    path = _kb_path(kb_name)
    if not os.path.exists(path):
        return False
    shutil.rmtree(path)
    return True


# ===================== 文档 =====================

def get_documents(kb_name: str) -> List[dict]:
    """获取知识库中的文档列表"""
    validate_kb_name(kb_name)
    docs_dir = _kb_docs_path(kb_name)
    if not os.path.exists(docs_dir):
        return []
    docs = []
    for f in sorted(os.listdir(docs_dir)):
        fp = os.path.join(docs_dir, f)
        if os.path.isfile(fp):
            size = os.path.getsize(fp)
            docs.append({
                "name": f,
                "size": size,
                "size_str": f"{size/1024:.1f} KB" if size > 1024 else f"{size} B",
                "path": fp,
            })
    return docs


def delete_document(kb_name: str, filename: str) -> bool:
    """删除知识库中的文档"""
    fp = safe_doc_path(kb_name, filename)
    if os.path.exists(fp):
        os.remove(fp)
        return True
    return False


def save_uploaded_file(kb_name: str, filename: str, data: bytes) -> tuple:
    """
    保存上传的文件到知识库（带安全检查）

    返回 (实际落盘路径, 落盘文件名)；落盘名带随机前缀，避免重名覆盖。
    """
    validate_kb_name(kb_name)

    # 安全校验：文件名
    filename = filename.strip().replace("\\", "/")
    if not filename or filename.startswith(".") or ".." in filename:
        raise ValueError("非法文件名")
    if len(filename) > 255:
        raise ValueError("文件名过长")

    # 安全校验：只允许白名单扩展名
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}")

    # 安全校验：文件大小（最大 50MB）
    MAX_SIZE = 50 * 1024 * 1024
    if len(data) > MAX_SIZE:
        raise ValueError(f"文件过大（最大 {MAX_SIZE // 1024 // 1024}MB）")

    # 内容体检：文档格式里出现脚本标记，只记日志不拦截
    # （用户完全可能在文档里讨论 <script>，一刀切会误伤）
    try:
        text_content = data.decode("utf-8", errors="ignore").lower()
        suspicious_patterns = [
            "<script", "<?php", "<html", "javascript:", "onload=",
            "onerror=", "onclick=", "vbscript:", "<%", "${",
        ]
        for pattern in suspicious_patterns:
            if pattern in text_content:
                logger.warning(f"文件内容含可疑脚本标记 ({pattern}): {filename}")
    except Exception:
        pass

    docs_dir = _kb_docs_path(kb_name)
    os.makedirs(docs_dir, exist_ok=True)

    # 加随机前缀防重名，再走统一的安全拼接
    safe_name = f"{secrets.token_hex(4)}_{os.path.basename(filename)}"
    fp = safe_doc_path(kb_name, safe_name)

    with open(fp, "wb") as f:
        f.write(data)

    return fp, safe_name


def get_documents_dir(kb_name: str) -> str:
    """获取知识库的文档目录路径（给 ingest 用）"""
    validate_kb_name(kb_name)
    return _kb_docs_path(kb_name)


def get_vector_store_dir(kb_name: str) -> str:
    """获取知识库的向量数据库路径（给 query 用）"""
    validate_kb_name(kb_name)
    return _kb_vector_path(kb_name)


def preview_document(kb_name: str, filename: str, max_chars: int = 1500) -> str:
    """预览文档内容（前 N 个字符）"""
    fp = safe_doc_path(kb_name, filename)
    if not os.path.exists(fp):
        return "[文件不存在]"

    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext in (".txt", ".md"):
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)
        elif ext == ".pdf":
            # 尝试用 PyMuPDF 读取
            try:
                import fitz
                doc = fitz.open(fp)
                text = ""
                for page in doc:
                    text += page.get_text()
                    if len(text) >= max_chars:
                        break
                doc.close()
                return text[:max_chars]
            except ImportError:
                return f"[PDF 文件: {filename}，安装 PyMuPDF 可预览内容]"
        elif ext == ".docx":
            try:
                from docx import Document
                doc = Document(fp)
                text = "\n".join(p.text for p in doc.paragraphs)
                return text[:max_chars]
            except ImportError:
                return f"[Word 文件: {filename}]"
        else:
            return f"[不支持预览: {filename}]"
    except Exception as e:
        return f"[预览失败: {e}]"


# ===================== 历史数据迁移 =====================

def migrate_ownerless_kbs(owner_id: str) -> int:
    """
    把没有归属的知识库划给指定用户（一次性历史数据迁移）

    早先创建的知识库 config.json 里没有 owner_id，
    加了归属校验后它们会变成谁都不拥有、谁也看不到。
    返回被迁移的知识库数量。
    """
    migrated = 0
    if os.path.exists(KB_ROOT):
        for name in sorted(os.listdir(KB_ROOT)):
            try:
                validate_kb_name(name)
            except ValueError:
                continue
            config_path = _kb_config_path(name)
            if not os.path.exists(config_path):
                continue
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
            if config.get("owner_id"):
                continue
            config["owner_id"] = owner_id
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            migrated += 1
            logger.info(f"知识库归属迁移: {name} -> {owner_id}")
    return migrated
