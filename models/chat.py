"""
聊天相关的数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class ChatSession(Base):
    """聊天会话"""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True)
    title = Column(String, default="新对话")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    model = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    is_pinned = Column(Boolean, default=False)
    is_temporary = Column(Boolean, default=False)
    folder_id = Column(String, ForeignKey("folders.id"), nullable=True)
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    folder = relationship("Folder", back_populates="chats")


class ChatMessage(Base):
    """聊天消息"""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String)  # user, assistant, system
    content = Column(Text)
    model = Column(String, nullable=True)
    tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    attachments = Column(JSON, default=list)
    meta_data = Column("meta_data", JSON, default=dict)
    
    session = relationship("ChatSession", back_populates="messages")


class Folder(Base):
    """文件夹"""
    __tablename__ = "folders"

    id = Column(String, primary_key=True)
    name = Column(String)
    parent_id = Column(String, ForeignKey("folders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    order = Column(Integer, default=0)
    
    chats = relationship("ChatSession", back_populates="folder")
    children = relationship("Folder", backref="parent", remote_side=[id])


# Pydantic 模型
class Message(BaseModel):
    """消息模型"""
    id: str
    role: str  # user, assistant, system
    content: str
    model: Optional[str] = None
    tokens: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    attachments: List[dict] = []
    meta_data: dict = {}


class Session(BaseModel):
    """会话模型"""
    id: str
    title: str = "新对话"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    model: Optional[str] = None
    provider: Optional[str] = None
    is_pinned: bool = False
    is_temporary: bool = False
    folder_id: Optional[str] = None
    messages: List[Message] = []


class FolderModel(BaseModel):
    """文件夹模型"""
    id: str
    name: str
    parent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    order: int = 0
