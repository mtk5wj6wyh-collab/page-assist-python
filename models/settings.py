"""
设置相关的数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean
from database import Base


class AppSettings(Base):
    """应用设置"""
    __tablename__ = "app_settings"

    id = Column(String, primary_key=True, default="app_settings")
    theme = Column(String, default="dark")
    font_size = Column(String, default="medium")
    sidebar_width = Column(String, default="medium")
    language = Column(String, default="zh-CN")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIProvider(Base):
    """AI提供商配置"""
    __tablename__ = "ai_providers"

    id = Column(String, primary_key=True)
    name = Column(String)
    provider_type = Column(String)  # ollama, openai, anthropic, etc.
    base_url = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    models = Column(JSON, default=list)
    is_default = Column(Boolean, default=False)
    settings = Column(JSON, default=dict)


class MCPServer(Base):
    """MCP服务器"""
    __tablename__ = "mcp_servers"

    id = Column(String, primary_key=True)
    name = Column(String)
    server_type = Column(String)  # stdio, sse
    command = Column(String, nullable=True)
    args = Column(JSON, default=list)
    env = Column(JSON, default=dict)
    url = Column(String, nullable=True)
    headers = Column(JSON, default=dict)
    auth_type = Column(String, default="none")  # none, api_key, oauth
    auth_config = Column(JSON, default=dict)
    is_enabled = Column(Boolean, default=True)
    tools = Column(JSON, default=list)


# Pydantic 模型
class SettingsModel(BaseModel):
    """设置模型"""
    id: str = "app_settings"
    theme: str = "dark"
    font_size: str = "medium"
    sidebar_width: str = "medium"
    language: str = "zh-CN"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AIProviderModel(BaseModel):
    """AI提供商模型"""
    id: str
    name: str
    provider_type: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: list = []
    is_default: bool = False
    settings: dict = {}


class MCPServerModel(BaseModel):
    """MCP服务器模型"""
    id: str
    name: str
    server_type: str
    command: Optional[str] = None
    args: list = []
    env: dict = {}
    url: Optional[str] = None
    headers: dict = {}
    auth_type: str = "none"
    auth_config: dict = {}
    is_enabled: bool = True
    tools: list = []
