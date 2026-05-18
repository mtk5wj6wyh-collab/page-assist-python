"""
RAG知识库服务
文档处理和向量检索
"""
import os
import uuid
from pathlib import Path
from typing import List, Optional, AsyncIterator
from abc import ABC, abstractmethod
import httpx
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings, DATA_DIR


class DocumentProcessor(ABC):
    """文档处理器基类"""
    
    @abstractmethod
    async def process(self, file_path: str) -> List[str]:
        """处理文档并返回文本块"""
        pass
    
    @abstractmethod
    def supports(self, file_type: str) -> bool:
        """检查是否支持该文件类型"""
        pass


class PDFProcessor(DocumentProcessor):
    """PDF文档处理器"""
    
    def supports(self, file_type: str) -> bool:
        return file_type.lower() in ["pdf"]
    
    async def process(self, file_path: str) -> List[str]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            chunks = []
            current_chunk = ""
            
            for page in reader.pages:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    if len(current_chunk) + len(line) > settings.rag.chunk_size:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = line
                    else:
                        current_chunk += " " + line
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else [""]
        except Exception as e:
            return [f"Error processing PDF: {str(e)}"]


class TextProcessor(DocumentProcessor):
    """文本文件处理器"""
    
    def supports(self, file_type: str) -> bool:
        return file_type.lower() in ["txt", "md", "csv", "json"]
    
    async def process(self, file_path: str) -> List[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            chunks = []
            lines = content.split("\n")
            current_chunk = ""
            
            for line in lines:
                if len(current_chunk) + len(line) > settings.rag.chunk_size:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = line
                else:
                    current_chunk += "\n" + line
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else [""]
        except Exception as e:
            return [f"Error processing text: {str(e)}"]


class DocxProcessor(DocumentProcessor):
    """Word文档处理器"""
    
    def supports(self, file_type: str) -> bool:
        return file_type.lower() in ["docx", "doc"]
    
    async def process(self, file_path: str) -> List[str]:
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            
            chunks = []
            current_chunk = ""
            
            for para in paragraphs:
                if len(current_chunk) + len(para) > settings.rag.chunk_size:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk += "\n" + para
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else [""]
        except Exception as e:
            return [f"Error processing DOCX: {str(e)}"]


class HtmlProcessor(DocumentProcessor):
    """HTML文档处理器"""
    
    def supports(self, file_type: str) -> bool:
        return file_type.lower() in ["html", "htm"]
    
    async def process(self, file_path: str) -> List[str]:
        try:
            from bs4 import BeautifulSoup
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            
            text = soup.get_text(separator="\n", strip=True)
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            
            chunks = []
            current_chunk = ""
            
            for para in paragraphs:
                if len(current_chunk) + len(para) > settings.rag.chunk_size:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk += "\n" + para
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else [""]
        except Exception as e:
            return [f"Error processing HTML: {str(e)}"]


class RAGService:
    """RAG知识库服务"""
    
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(
            path=str(DATA_DIR / "chroma_db"),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_model = settings.rag.embedding_model
        self.providers: List[DocumentProcessor] = [
            PDFProcessor(),
            TextProcessor(),
            DocxProcessor(),
            HtmlProcessor(),
        ]
    
    def get_processor(self, file_type: str) -> Optional[DocumentProcessor]:
        """获取合适的处理器"""
        for provider in self.providers:
            if provider.supports(file_type):
                return provider
        return None
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入"""
        try:
            client = httpx.AsyncClient(timeout=30.0)
            url = f"{settings.ai.ollama_base_url}/api/embeddings"
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            await client.aclose()
            return data["embedding"]
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            import numpy as np
            return np.random.rand(768).tolist()
    
    async def add_document(
        self,
        knowledge_base_id: str,
        file_path: str,
        file_name: str,
        file_type: str
    ) -> str:
        """添加文档到知识库"""
        processor = self.get_processor(file_type)
        if not processor:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        chunks = await processor.process(file_path)
        
        doc_id = str(uuid.uuid4())
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            embedding = await self.generate_embedding(chunk)
            
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append({
                "knowledge_base_id": knowledge_base_id,
                "document_id": doc_id,
                "document_name": file_name,
                "chunk_index": i
            })
        
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
        
        return doc_id
    
    async def retrieve(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        top_k: int = None
    ) -> List[dict]:
        """检索相关文档"""
        if top_k is None:
            top_k = settings.rag.retrieval_top_k
        
        query_embedding = await self.generate_embedding(query)
        
        where_filter = {"knowledge_base_id": knowledge_base_id} if knowledge_base_id else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )
        
        retrieved = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                retrieved.append({
                    "content": doc,
                    "score": float(results["distances"][0][i]) if results.get("distances") else 0.0,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}
                })
        
        return retrieved
    
    def delete_document(self, doc_id: str):
        """删除文档"""
        try:
            results = self.collection.get()
            ids_to_delete = [id for id in results["ids"] if id.startswith(doc_id)]
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
        except Exception as e:
            print(f"Error deleting document: {e}")
    
    def delete_knowledge_base(self, knowledge_base_id: str):
        """删除整个知识库"""
        try:
            self.collection.delete(where={"knowledge_base_id": knowledge_base_id})
        except Exception as e:
            print(f"Error deleting knowledge base: {e}")
