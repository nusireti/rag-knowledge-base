"""
知识库管理
支持多个知识库的创建、切换、删除
每个知识库有独立的文档目录和向量数据库
"""

import os
import json
import secrets
import shutil
from pathlib import Path
from typing import List, Optional

# 知识库存储根目录
KB_ROOT = os.path.join(os.path.dirname(__file__), "knowledge_bases")
os.makedirs(KB_ROOT, exist_ok=True)


def _kb_path(kb_name: str) -> str:
    return os.path.join(KB_ROOT, kb_name)


def _kb_config_path(kb_name: str) -> str:
    return os.path.join(_kb_path(kb_name), "config.json")


def _kb_docs_path(kb_name: str) -> str:
    return os.path.join(_kb_path(kb_name), "documents")


def _kb_vector_path(kb_name: str) -> str:
    return os.path.join(_kb_path(kb_name), "vector_store")


def list_knowledge_bases() -> List[dict]:
    """列出所有知识库"""
    kbs = []
    if not os.path.exists(KB_ROOT):
        return kbs
    for name in sorted(os.listdir(KB_ROOT)):
        kbs.append(get_knowledge_base_info(name))
    # 过滤掉无效的
    return [kb for kb in kbs if kb is not None]


def get_knowledge_base_info(kb_name: str) -> Optional[dict]:
    """获取知识库信息"""
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
    }


def create_knowledge_base(name: str, display_name: str = "", description: str = "") -> bool:
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
    }
    with open(_kb_config_path(safe_name), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return True


def delete_knowledge_base(kb_name: str) -> bool:
    """删除知识库"""
    path = _kb_path(kb_name)
    if not os.path.exists(path):
        return False
    shutil.rmtree(path)
    return True


def get_documents(kb_name: str) -> List[dict]:
    """获取知识库中的文档列表"""
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
    fp = os.path.join(_kb_docs_path(kb_name), filename)
    if os.path.exists(fp):
        os.remove(fp)
        return True
    return False


def save_uploaded_file(kb_name: str, filename: str, data: bytes) -> str:
    """保存上传的文件到知识库（带安全检查）"""
    # 安全校验：文件名
    filename = filename.strip().replace("\\", "/")
    if not filename or filename.startswith(".") or ".." in filename:
        raise ValueError("非法文件名")
    if len(filename) > 255:
        raise ValueError("文件名过长")

    # 安全校验：只允许白名单扩展名
    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}")

    # 安全校验：文件大小（最大 50MB）
    MAX_SIZE = 50 * 1024 * 1024
    if len(data) > MAX_SIZE:
        raise ValueError(f"文件过大（最大 {MAX_SIZE // 1024 // 1024}MB）")

    # 安全校验：内容安全检查（禁止脚本、HTML 等）
    try:
        text_content = data.decode("utf-8", errors="ignore").lower()
        suspicious_patterns = [
            "<script", "<?php", "<html", "javascript:", "onload=",
            "onerror=", "onclick=", "vbscript:", "<%", "${",
        ]
        for pattern in suspicious_patterns:
            if pattern in text_content:
                # 允许脚本内容出现在 .py .js 等编程文件中，但我们的白名单只有文档格式
                # 对于文档格式，脚本内容是可疑的
                if ext in (".txt", ".md", ".pdf", ".docx"):
                    logger.warning(f"文件内容含可疑脚本标记 ({pattern}): {filename}")
                    # 不阻止，仅记录日志（用户可能只是文档中提到了这个词）
    except Exception:
        pass

    docs_dir = _kb_docs_path(kb_name)
    os.makedirs(docs_dir, exist_ok=True)

    # 防止路径遍历攻击
    safe_name = f"{secrets.token_hex(4)}_{filename}"
    fp = os.path.normpath(os.path.join(docs_dir, safe_name))
    if not fp.startswith(os.path.normpath(docs_dir)):
        raise ValueError("路径遍历攻击已拦截")

    with open(fp, "wb") as f:
        f.write(data)

    return fp, safe_name


def get_documents_dir(kb_name: str) -> str:
    """获取知识库的文档目录路径（给 ingest 用）"""
    return _kb_docs_path(kb_name)


def get_vector_store_dir(kb_name: str) -> str:
    """获取知识库的向量数据库路径（给 query 用）"""
    return _kb_vector_path(kb_name)


def preview_document(kb_name: str, filename: str, max_chars: int = 1500) -> str:
    """预览文档内容（前 N 个字符）"""
    fp = os.path.join(_kb_docs_path(kb_name), filename)
    if not os.path.exists(fp):
        return "[文件不存在]"

    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext == ".txt":
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)
        elif ext == ".md":
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
