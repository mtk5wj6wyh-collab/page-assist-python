"""
聊天管理服务
处理聊天会话和消息
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, AsyncIterator
import json
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import ChatSession, ChatMessage, Folder, Message, Session
from services.ai_provider import AIProviderFactory
from services.search import SearchService
from services.rag import RAGService
from config import settings


class ChatManager:
    """聊天管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_factory = AIProviderFactory()
        self.search_service = SearchService()
        self.rag_service = RAGService()
    
    # ========== 会话管理 ==========
    
    async def create_session(
        self,
        title: str = "新对话",
        model: str = None,
        provider: str = None,
        folder_id: str = None,
        is_temporary: bool = False
    ) -> ChatSession:
        """创建新会话"""
        session = ChatSession(
            id=str(uuid.uuid4()),
            title=title,
            model=model or settings.ai.default_provider,
            provider=provider or settings.ai.default_provider,
            folder_id=folder_id,
            is_temporary=is_temporary
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def get_sessions(
        self,
        folder_id: Optional[str] = None,
        include_temporary: bool = False,
        limit: int = 100
    ) -> List[ChatSession]:
        """获取会话列表"""
        query = select(ChatSession)
        
        if folder_id:
            query = query.where(ChatSession.folder_id == folder_id)
        
        if not include_temporary:
            query = query.where(ChatSession.is_temporary == False)
        
        query = query.order_by(ChatSession.updated_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_session(
        self,
        session_id: str,
        title: str = None,
        model: str = None,
        is_pinned: bool = None
    ) -> Optional[ChatSession]:
        """更新会话"""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        if title is not None:
            session.title = title
        if model is not None:
            session.model = model
        if is_pinned is not None:
            session.is_pinned = is_pinned
        
        session.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        result = await self.db.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        result = await self.db.execute(
            delete(ChatSession).where(ChatSession.id == session_id)
        )
        await self.db.commit()
        return True
    
    # ========== 消息管理 ==========
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model: str = None,
        attachments: List[dict] = None
    ) -> ChatMessage:
        """添加消息"""
        message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            attachments=attachments or []
        )
        self.db.add(message)
        
        # 更新会话时间
        session = await self.get_session(session_id)
        if session:
            session.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(message)
        return message
    
    async def get_messages(self, session_id: str) -> List[ChatMessage]:
        """获取会话消息"""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())
    
    async def delete_message(self, message_id: str) -> bool:
        """删除消息"""
        result = await self.db.execute(
            delete(ChatMessage).where(ChatMessage.id == message_id)
        )
        await self.db.commit()
        return True
    
    # ========== AI对话 ==========
    
    async def chat(
        self,
        session_id: str,
        user_message: str,
        provider: str = None,
        model: str = None,
        enable_search: bool = False,
        knowledge_base_id: str = None,
        system_prompt: str = None
    ) -> str:
        """发送消息并获取AI回复"""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session()
        
        # 添加用户消息
        await self.add_message(session_id, "user", user_message)
        
        # 构建消息历史
        messages_history = await self.get_messages(session_id)
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史消息
        for msg in messages_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # 如果启用搜索，添加搜索结果
        if enable_search and settings.search.search_enabled:
            search_context = await self.search_service.search_with_context(
                user_message,
                num_results=3
            )
            search_prompt = f"\n\n[网络搜索结果]\n{search_context}\n\n请基于以上搜索结果回答问题。"
            messages.append({"role": "system", "content": search_prompt})
        
        # 如果启用了RAG，检索相关文档
        if knowledge_base_id and settings.rag.rag_enabled:
            retrieved_docs = await self.rag_service.retrieve(
                user_message,
                knowledge_base_id=knowledge_base_id,
                top_k=3
            )
            if retrieved_docs:
                rag_context = "\n\n[相关文档内容]\n"
                for i, doc in enumerate(retrieved_docs, 1):
                    rag_context += f"\n文档{i}: {doc['content']}\n"
                messages.append({"role": "system", "content": rag_context})
        
        # 调用AI
        provider = provider or session.provider or settings.ai.default_provider
        ai_provider = self.ai_factory.create(provider)
        
        try:
            response = await ai_provider.chat(messages, model=model)
            
            # 添加AI回复
            await self.add_message(session_id, "assistant", response, model=model)
            
            return response
        finally:
            await ai_provider.close()
    
    async def chat_stream(
        self,
        session_id: str,
        user_message: str,
        provider: str = None,
        model: str = None,
        enable_search: bool = False,
        knowledge_base_id: str = None,
        system_prompt: str = None
    ) -> AsyncIterator[str]:
        """流式对话"""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session()
        
        # 添加用户消息
        await self.add_message(session_id, "user", user_message)
        
        # 构建消息历史
        messages_history = await self.get_messages(session_id)
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        if enable_search and settings.search.search_enabled:
            search_context = await self.search_service.search_with_context(
                user_message,
                num_results=3
            )
            messages.append({"role": "system", "content": f"\n\n[网络搜索结果]\n{search_context}\n\n"})

        provider = provider or session.provider or settings.ai.default_provider
        ai_provider = self.ai_factory.create(provider)
        
        full_response = ""
        try:
            async for chunk in ai_provider.chat_stream(messages, model=model):
                full_response += chunk
                yield chunk
            
            await self.add_message(session_id, "assistant", full_response, model=model)
        finally:
            await ai_provider.close()
    
    # ========== 文件夹管理 ==========
    
    async def create_folder(self, name: str, parent_id: str = None) -> Folder:
        """创建文件夹"""
        folder = Folder(
            id=str(uuid.uuid4()),
            name=name,
            parent_id=parent_id
        )
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder
    
    async def get_folders(self) -> List[Folder]:
        """获取所有文件夹"""
        result = await self.db.execute(
            select(Folder).order_by(Folder.order, Folder.name)
        )
        return list(result.scalars().all())
    
    async def delete_folder(self, folder_id: str) -> bool:
        """删除文件夹"""
        # 将文件夹中的会话移到根目录
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.folder_id == folder_id)
            .values(folder_id=None)
        )
        
        result = await self.db.execute(
            delete(Folder).where(Folder.id == folder_id)
        )
        await self.db.commit()
        return True


# 全局聊天管理器实例
_chat_managers: Dict[str, ChatManager] = {}


def get_chat_manager(db: AsyncSession) -> ChatManager:
    """获取聊天管理器"""
    return ChatManager(db)
