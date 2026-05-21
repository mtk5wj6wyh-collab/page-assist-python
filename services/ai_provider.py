"""
AI提供商服务
统一的AI模型调用接口
"""
import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any, List
import httpx
from config import settings


class BaseAIProvider(ABC):
    """AI提供商基类"""
    
    @abstractmethod
    async def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送聊天请求"""
        pass
    
    @abstractmethod
    async def chat_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """流式聊天"""
        pass
    
    @abstractmethod
    async def get_models(self) -> List[str]:
        """获取可用模型列表"""
        pass


class OllamaProvider(BaseAIProvider):
    """Ollama本地模型提供商"""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ai.ollama_base_url
        self.model = model or settings.ai.ollama_model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送聊天请求"""
        model = kwargs.get("model", self.model)
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if "temperature" in kwargs:
            payload["options"] = {"temperature": kwargs["temperature"]}
        if "max_tokens" in kwargs:
            payload["options"] = payload.get("options", {})
            payload["options"]["num_predict"] = kwargs["max_tokens"]
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
    
    async def chat_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """流式聊天"""
        model = kwargs.get("model", self.model)
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        if "temperature" in kwargs:
            payload["options"] = {"temperature": kwargs["temperature"]}
        
        async with self.client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except json.JSONDecodeError:
                        continue
    
    async def get_models(self) -> List[str]:
        """获取可用模型列表"""
        url = f"{self.base_url}/api/tags"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        models = [m["name"] for m in data.get("models", [])]
        if not models:
            raise ValueError("Ollama 未返回任何模型，请检查 Ollama 服务是否运行")
        return models
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入"""
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": settings.rag.embedding_model, "prompt": text}
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["embedding"]
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class OpenAIProvider(BaseAIProvider):
    """OpenAI API提供商"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key
        self.base_url = base_url or settings.ai.openai_base_url
        self.model = model or settings.ai.openai_model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送聊天请求"""
        model = kwargs.get("model", self.model)
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        
        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    async def chat_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """流式聊天"""
        model = kwargs.get("model", self.model)
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        
        async with self.client.stream("POST", url, json=payload, headers=self._get_headers()) as response:
            async for line in response.aiter_lines():
                if line and line.startswith("data: "):
                    if line.strip() == "data: [DONE]":
                        break
                    try:
                        data = json.loads(line[6:])
                        if content := data["choices"][0]["delta"].get("content"):
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    async def get_models(self) -> List[str]:
        """获取可用模型列表"""
        url = f"{self.base_url}/models"
        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        models = [m["id"] for m in data["data"]]
        if not models:
            raise ValueError("API 返回的模型列表为空，请检查 API Key 是否正确")
        return models
    
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入"""
        url = f"{self.base_url}/embeddings"
        payload = {"model": "text-embedding-3-small", "input": text}
        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude提供商"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.ai.anthropic_api_key
        self.model = model or settings.ai.anthropic_model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    async def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送聊天请求"""
        # Anthropic使用不同的消息格式
        formatted_messages = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": formatted_messages,
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        
        response = await self.client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    
    async def chat_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """流式聊天 - Anthropic不支持真正的流式，这里模拟"""
        content = await self.chat(messages, **kwargs)
        for char in content:
            yield char
    
    async def get_models(self) -> List[str]:
        """获取可用模型"""
        return ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
    
    async def close(self):
        await self.client.aclose()


class GoogleProvider(BaseAIProvider):
    """Google Gemini提供商"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.ai.google_api_key
        self.model = model or settings.ai.google_model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat(self, messages: List[Dict], **kwargs) -> str:
        """发送聊天请求"""
        model = kwargs.get("model", self.model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            contents.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })
        
        payload = {"contents": contents}
        if "temperature" in kwargs:
            payload["generationConfig"] = {"temperature": kwargs["temperature"]}
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    
    async def chat_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """流式聊天"""
        model = kwargs.get("model", self.model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"
        
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            contents.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })
        
        payload = {"contents": contents}
        if "temperature" in kwargs:
            payload["generationConfig"] = {"temperature": kwargs["temperature"]}
        
        async with self.client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "candidates" in data and data["candidates"]:
                            for part in data["candidates"][0].get("content", {}).get("parts", []):
                                if "text" in part:
                                    yield part["text"]
                    except json.JSONDecodeError:
                        continue
    
    async def get_models(self) -> List[str]:
        """获取可用模型（通过API动态获取）"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        models = [m["name"].replace("models/", "") for m in data.get("models", [])]
        if not models:
            raise ValueError("API 返回的模型列表为空，请检查 API Key 是否正确")
        return models
    
    async def close(self):
        await self.client.aclose()


class GroqProvider(OpenAIProvider):
    """Groq高速推理提供商 (兼容OpenAI API)"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        super().__init__(
            api_key=api_key or settings.ai.groq_api_key,
            base_url=base_url or settings.ai.groq_base_url,
            model=model or settings.ai.groq_model
        )

    async def get_models(self) -> List[str]:
        """获取可用模型列表"""
        url = f"{self.base_url}/models"
        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            models = [m["id"] for m in data["data"]]
            if not models:
                raise ValueError("API 返回的模型列表为空")
            return models
        raise ValueError("API 响应格式异常，请检查 API 地址是否正确")


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek AI提供商 (兼容OpenAI API)"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        super().__init__(
            api_key=api_key or settings.ai.deepseek_api_key,
            base_url=base_url or settings.ai.deepseek_base_url,
            model=model or settings.ai.deepseek_model
        )

    async def get_models(self) -> List[str]:
        """获取可用模型列表"""
        url = f"{self.base_url}/models"
        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            models = [m["id"] for m in data["data"]]
            if not models:
                raise ValueError("API 返回的模型列表为空")
            return models
        raise ValueError("API 响应格式异常，请检查 API 地址是否正确")


class MistralProvider(OpenAIProvider):
    """Mistral AI提供商 (兼容OpenAI API)"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        super().__init__(
            api_key=api_key or settings.ai.mistral_api_key,
            base_url=base_url or settings.ai.mistral_base_url,
            model=model or settings.ai.mistral_model
        )

    async def get_models(self) -> List[str]:
        """获取可用模型列表"""
        url = f"{self.base_url}/models"
        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            models = [m["id"] for m in data["data"]]
            if not models:
                raise ValueError("API 返回的模型列表为空")
            return models
        raise ValueError("API 响应格式异常，请检查 API 地址是否正确")


class MoonshotProvider(OpenAIProvider):
    """Moonshot (Kimi) AI提供商 (兼容OpenAI API)"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        super().__init__(
            api_key=api_key or settings.ai.moonshot_api_key,
            base_url=base_url or settings.ai.moonshot_base_url,
            model=model or settings.ai.moonshot_model
        )

    async def get_models(self) -> List[str]:
        """获取可用模型列表"""
        url = f"{self.base_url}/models"
        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            models = [m["id"] for m in data["data"]]
            if not models:
                raise ValueError("API 返回的模型列表为空")
            return models
        raise ValueError("API 响应格式异常，请检查 API 地址是否正确")


class MiMoProvider(OpenAIProvider):
    """Xiaomi MiMo AI提供商 (兼容OpenAI API)"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        super().__init__(
            api_key=api_key or settings.ai.mimo_api_key,
            base_url=base_url or settings.ai.mimo_base_url,
            model=model or settings.ai.mimo_model
        )

    async def get_models(self) -> List[str]:
        """获取可用模型列表（通过API动态获取）"""
        url = f"{self.base_url}/models"
        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        models = [m["id"] for m in data.get("data", [])]
        if not models:
            raise ValueError("API 返回的模型列表为空，请检查 API Key 是否正确")
        return models


# 提供商工厂
class AIProviderFactory:
    """AI提供商工厂"""
    
    _providers: Dict[str, type] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "groq": GroqProvider,
        "deepseek": DeepSeekProvider,
        "mistral": MistralProvider,
        "moonshot": MoonshotProvider,
        "mimo": MiMoProvider,
    }
    
    @classmethod
    def create(cls, provider_type: str, **kwargs) -> BaseAIProvider:
        """创建提供商实例"""
        provider_class = cls._providers.get(provider_type, OllamaProvider)
        return provider_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, provider_class: type):
        """注册新的提供商"""
        cls._providers[name] = provider_class
