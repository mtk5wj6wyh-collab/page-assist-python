"""
提示词相关的数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, JSON
from database import Base


class Prompt(Base):
    """提示词"""
    __tablename__ = "prompts"

    id = Column(String, primary_key=True)
    name = Column(String)
    content = Column(Text)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    category = Column(String, default="custom")
    is_default = Column(Boolean, default=False)
    is_copilot = Column(Boolean, default=False)
    trigger = Column(String, nullable=True)
    variables = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    use_count = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False)


class CopilotPrompt(Base):
    """Copilot提示词"""
    __tablename__ = "copilot_prompts"

    id = Column(String, primary_key=True)
    name = Column(String)
    content = Column(Text)
    description = Column(Text, nullable=True)
    trigger = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic 模型
class PromptModel(BaseModel):
    """提示词模型"""
    id: str
    name: str
    content: str
    description: Optional[str] = None
    tags: List[str] = []
    category: str = "custom"
    is_default: bool = False
    is_copilot: bool = False
    trigger: Optional[str] = None
    variables: List[dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    use_count: int = 0
    is_favorite: bool = False


class CopilotPromptModel(BaseModel):
    """Copilot提示词模型"""
    id: str
    name: str
    content: str
    description: Optional[str] = None
    trigger: Optional[str] = None
    is_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
