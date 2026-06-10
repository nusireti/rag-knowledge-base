"""
ORM 模型定义
用户、知识库、文档、对话记录 的数据模型
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _short_uuid() -> str:
    return uuid.uuid4().hex[:12]


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=_short_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True)
    password_hash = Column(String(256), nullable=False)
    display_name = Column(String(64), default="")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    last_login_at = Column(DateTime, nullable=True)
    preferences = Column(JSON, default=dict)

    # 关系
    knowledge_bases = relationship("KnowledgeBase", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_bases"

    id = Column(String(32), primary_key=True, default=_short_uuid)
    name = Column(String(64), nullable=False)
    display_name = Column(String(128), default="")
    description = Column(Text, default="")
    owner_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)
    retrieval_k = Column(Integer, default=6)
    doc_count = Column(Integer, default=0)
    vector_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    owner = relationship("User", back_populates="knowledge_bases")
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="knowledge_base")

    @property
    def vector_store_path(self) -> str:
        from app.config import settings
        return str(settings.vector_store_dir / self.id)

    @property
    def documents_path(self) -> str:
        from app.config import settings
        path = settings.documents_dir / self.id
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def __repr__(self) -> str:
        return f"<KB {self.display_name or self.name}>"


class Document(Base):
    """文档模型"""
    __tablename__ = "documents"

    id = Column(String(32), primary_key=True, default=_short_uuid)
    filename = Column(String(256), nullable=False)
    original_filename = Column(String(256), nullable=False)
    file_size = Column(Integer, default=0)
    file_type = Column(String(16), nullable=False)  # pdf, txt, md, docx
    page_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    kb_id = Column(String(32), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(String(32), ForeignKey("users.id"), nullable=True)
    storage_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Doc {self.original_filename}>"


class Conversation(Base):
    """对话记录模型"""
    __tablename__ = "conversations"

    id = Column(String(32), primary_key=True, default=_short_uuid)
    title = Column(String(256), default="新对话")
    owner_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    kb_id = Column(String(32), ForeignKey("knowledge_bases.id"), nullable=True)
    message_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    is_starred = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    owner = relationship("User", back_populates="conversations")
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")

    def __repr__(self) -> str:
        return f"<Conv {self.title}>"


class Message(Base):
    """消息模型"""
    __tablename__ = "messages"

    id = Column(String(32), primary_key=True, default=_short_uuid)
    conversation_id = Column(String(32), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # 引用文档来源
    tokens = Column(Integer, default=0)
    feedback = Column(String(16), nullable=True)  # like, dislike
    created_at = Column(DateTime, default=_utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Msg {self.role}: {self.content[:30]}...>"
