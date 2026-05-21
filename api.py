"""
FastAPI 后端服务
提供REST API接口
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import uvicorn

from config import settings
from database import init_db, get_db_context
from services.ai_provider import AIProviderFactory
from services.chat_manager import ChatManager
from services.rag import RAGService
from services.search import SearchService
from services.tts import TTSService
from services.prompt_manager import PromptManager

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="Page Assist Python Edition API",
    version=settings.app_version
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 请求/响应模型 ==========

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    enable_search: bool = False
    knowledge_base_id: Optional[str] = None


class SessionCreate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class PromptCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    tags: List[str] = []
    category: str = "custom"
    is_copilot: bool = False
    trigger: Optional[str] = None


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    embedding_model: str = "nomic-embed-text"
    chunk_size: int = 500
    chunk_overlap: int = 100


# ========== 启动事件 ==========

@app.on_event("startup")
async def startup():
    await init_db()


# ========== 健康检查 ==========

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}


# ========== AI对话接口 ==========

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """发送消息并获取AI回复"""
    async with get_db_context() as db:
        chat_manager = ChatManager(db)
        
        # 创建或获取会话
        if request.session_id:
            session = await chat_manager.get_session(request.session_id)
            if not session:
                session = await chat_manager.create_session()
        else:
            session = await chat_manager.create_session()
        
        # 调用AI
        response = await chat_manager.chat(
            session_id=session.id,
            user_message=request.message,
            provider=request.provider,
            model=request.model,
            enable_search=request.enable_search,
            knowledge_base_id=request.knowledge_base_id,
            system_prompt=request.system_prompt
        )
        
        return {
            "session_id": session.id,
            "response": response
        }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话"""
    async def generate():
        async with get_db_context() as db:
            chat_manager = ChatManager(db)
            
            if request.session_id:
                session = await chat_manager.get_session(request.session_id)
                if not session:
                    session = await chat_manager.create_session()
            else:
                session = await chat_manager.create_session()
            
            async for chunk in chat_manager.chat_stream(
                session_id=session.id,
                user_message=request.message,
                provider=request.provider,
                model=request.model,
                enable_search=request.enable_search,
                knowledge_base_id=request.knowledge_base_id,
                system_prompt=request.system_prompt
            ):
                yield f"data: {chunk}\n\n"
            
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )


# ========== 会话管理 ==========

@app.get("/api/sessions")
async def get_sessions():
    """获取所有会话"""
    async with get_db_context() as db:
        chat_manager = ChatManager(db)
        sessions = await chat_manager.get_sessions()
        return [
            {
                "id": s.id,
                "title": s.title,
                "model": s.model,
                "provider": s.provider,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "is_pinned": s.is_pinned
            }
            for s in sessions
        ]


@app.post("/api/sessions")
async def create_session(request: SessionCreate):
    """创建新会话"""
    async with get_db_context() as db:
        chat_manager = ChatManager(db)
        session = await chat_manager.create_session(
            title=request.title or "新对话",
            model=request.model,
            provider=request.provider
        )
        return {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat()
        }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    async with get_db_context() as db:
        chat_manager = ChatManager(db)
        session = await chat_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, message="Session not found")
        
        messages = await chat_manager.get_messages(session_id)
        
        return {
            "id": session.id,
            "title": session.title,
            "model": session.model,
            "provider": session.provider,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ]
        }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    async with get_db_context() as db:
        chat_manager = ChatManager(db)
        await chat_manager.delete_session(session_id)
        return {"status": "deleted"}


# ========== 提示词管理 ==========

@app.get("/api/prompts")
async def get_prompts(category: Optional[str] = None):
    """获取提示词列表"""
    async with get_db_context() as db:
        prompt_manager = PromptManager(db)
        prompts = await prompt_manager.get_prompts(category=category)
        return [
            {
                "id": p.id,
                "name": p.name,
                "content": p.content,
                "description": p.description,
                "tags": p.tags,
                "category": p.category,
                "is_copilot": p.is_copilot,
                "trigger": p.trigger,
                "use_count": p.use_count
            }
            for p in prompts
        ]


@app.post("/api/prompts")
async def create_prompt(request: PromptCreate):
    """创建提示词"""
    async with get_db_context() as db:
        prompt_manager = PromptManager(db)
        prompt = await prompt_manager.create_prompt(
            name=request.name,
            content=request.content,
            description=request.description,
            tags=request.tags,
            category=request.category,
            is_copilot=request.is_copilot,
            trigger=request.trigger
        )
        return {
            "id": prompt.id,
            "name": prompt.name
        }


# ========== 知识库 ==========

@app.get("/api/knowledge")
async def get_knowledge_bases():
    """获取知识库列表"""
    # 简化实现
    return []


@app.post("/api/knowledge")
async def create_knowledge_base(request: KnowledgeBaseCreate):
    """创建知识库"""
    # 简化实现
    return {"id": "new_id", "name": request.name}


@app.post("/api/knowledge/{kb_id}/upload")
async def upload_document(kb_id: str, file: bytes, filename: str):
    """上传文档"""
    rag_service = RAGService()
    
    # 保存文件
    from pathlib import Path
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / filename
    with open(file_path, "wb") as f:
        f.write(file)
    
    # 处理文档
    file_type = Path(filename).suffix.lstrip(".")
    doc_id = await rag_service.add_document(
        knowledge_base_id=kb_id,
        file_path=str(file_path),
        file_name=filename,
        file_type=file_type
    )
    
    return {"document_id": doc_id, "filename": filename}


@app.post("/api/knowledge/{kb_id}/search")
async def search_knowledge(kb_id: str, query: str, top_k: int = 5):
    """检索知识库"""
    rag_service = RAGService()
    results = await rag_service.retrieve(
        query=query,
        knowledge_base_id=kb_id,
        top_k=top_k
    )
    return {"results": results}


# ========== 搜索 ==========

@app.get("/api/search")
async def search(query: str, provider: Optional[str] = None, num_results: int = 5):
    """执行搜索"""
    search_service = SearchService()
    results = await search_service.search(
        query=query,
        provider=provider,
        num_results=num_results
    )
    return {"results": results}


# ========== TTS ==========

@app.post("/api/tts")
async def text_to_speech(text: str, provider: Optional[str] = None):
    """文字转语音"""
    tts_service = TTSService()
    
    # 清理文本
    cleaned_text = tts_service.clean_text_for_tts(text)
    
    # 生成语音
    audio_data = await tts_service.synthesize(cleaned_text, provider=provider)
    
    return StreamingResponse(
        iter([audio_data]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=tts.mp3"}
    )


# ========== AI模型 ==========

@app.get("/api/models")
async def get_models(provider: str = None):
    """获取可用模型列表"""
    if provider:
        return AIProviderFactory._providers.get(provider, {}).get("models", [])
    
    all_models = {}
    for name, info in AIProviderFactory._providers.items():
        all_models[name] = info.get("models", [])
    
    return all_models


@app.get("/api/models/{provider}/list")
async def get_provider_models(provider: str):
    """获取特定提供商的模型列表"""
    ai_provider = AIProviderFactory.create(provider)
    try:
        models = await ai_provider.get_models()
        return {"models": models}
    except Exception as e:
        return {"error": f"无法获取模型列表: {str(e)}", "hint": "请检查 API Key 和网络连接，或手动配置模型名称"}
    finally:
        await ai_provider.close()


# ========== 运行服务器 ==========

def run_server():
    """运行API服务器"""
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    run_server()
