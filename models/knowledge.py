"""
知识库相关的数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, JSON
from database import Base


class KnowledgeBase(Base):
    """知识库"""
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    embedding_model = Column(String, default="nomic-embed-text")
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    doc_count = Column(Integer, default=0)


class Document(Base):
    """文档"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    knowledge_base_id = Column(String)
    filename = Column(String)
    file_path = Column(String)
    file_type = Column(String)
    file_size = Column(Integer)
    status = Column(String, default="pending")  # pending, processing, completed, error
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    meta_data = Column("meta_data", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class Chunk(Base):
    """文本块"""
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    document_id = Column(String)
    content = Column(Text)
    chunk_index = Column(Integer)
    page_number = Column(Integer, nullable=True)
    meta_data = Column("meta_data", JSON, default=dict)


# Pydantic 模型
class KnowledgeBaseModel(BaseModel):
    """知识库模型"""
    id: str
    name: str
    description: Optional[str] = None
    embedding_model: str = "nomic-embed-text"
    chunk_size: int = 500
    chunk_overlap: int = 100
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    doc_count: int = 0


class DocumentModel(BaseModel):
    """文档模型"""
    id: str
    knowledge_base_id: str
    filename: str
    file_type: str
    file_size: int
    status: str = "pending"
    chunk_count: int = 0
    error_message: Optional[str] = None
    metadata: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None


class RetrievalResult(BaseModel):
    """检索结果"""
    content: str
    document_id: str
    document_name: str
    chunk_id: str
    score: float
    metadata: dict = {}
