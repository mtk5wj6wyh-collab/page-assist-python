"""
TTS语音合成服务
文字转语音功能
"""
import base64
import json
from typing import Optional
import httpx
from abc import ABC, abstractmethod
from config import settings


class BaseTTSProvider(ABC):
    """TTS提供商基类"""
    
    @abstractmethod
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """合成语音"""
        pass


class BrowserTTSProvider(BaseTTSProvider):
    """浏览器TTS（前端使用）"""
    
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """浏览器TTS由前端实现，这里返回占位数据"""
        return b""


class ElevenLabsTTS(BaseTTSProvider):
    """ElevenLabs高质量语音"""
    
    def __init__(self, api_key: str = None, voice_id: str = None):
        self.api_key = api_key or settings.tts.elevenlabs_api_key
        self.voice_id = voice_id or settings.tts.elevenlabs_voice_id
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """合成语音"""
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": kwargs.get("stability", 0.5),
                    "similarity_boost": kwargs.get("similarity_boost", 0.75),
                    "style": kwargs.get("style", 0.0),
                    "use_speaker_boost": kwargs.get("use_speaker_boost", True)
                }
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"ElevenLabs TTS error: {str(e)}")
    
    async def close(self):
        await self.client.aclose()


class OpenAITTS(BaseTTSProvider):
    """OpenAI TTS"""
    
    def __init__(self, api_key: str = None, model: str = None, voice: str = None):
        self.api_key = api_key or settings.ai.openai_api_key
        self.model = model or settings.tts.openai_tts_model
        self.voice = voice or settings.tts.openai_tts_voice
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """合成语音"""
        try:
            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "input": text,
                "voice": self.voice,
                "speed": kwargs.get("speed", settings.tts.tts_speed)
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"OpenAI TTS error: {str(e)}")
    
    async def close(self):
        await self.client.aclose()


class EdgeTTSProvider(BaseTTSProvider):
    """Edge TTS（免费高质量）"""
    
    def __init__(self, voice: str = None):
        self.voice = voice or settings.tts.edge_tts_voice
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """合成语音"""
        try:
            url = "https://speech.platform.bing.com/ speech /tts/crosslinguish"
            headers = {
                "Ocp-Apim-Subscription-Key": "your-key",  # 需要Azure认知服务密钥
            }
            
            # 使用edge-tts Python库
            import subprocess
            result = subprocess.run([
                "npx", "-y", "@langchain-community/edge-tts",
                "--text", text,
                "--voice", self.voice,
                "--output", "/tmp/tts_output.mp3"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                with open("/tmp/tts_output.mp3", "rb") as f:
                    return f.read()
            else:
                # 如果npx失败，返回错误
                raise Exception(f"Edge TTS failed: {result.stderr}")
        except Exception as e:
            raise Exception(f"Edge TTS error: {str(e)}")
    
    async def close(self):
        await self.client.aclose()


class TTSService:
    """TTS服务"""
    
    def __init__(self):
        self.current_provider: Optional[BaseTTSProvider] = None
        self.providers = {}
    
    def get_provider(self, provider_type: str = None) -> BaseTTSProvider:
        """获取TTS提供商"""
        if provider_type is None:
            provider_type = settings.tts.tts_provider
        
        if provider_type not in self.providers:
            if provider_type == "elevenlabs":
                self.providers[provider_type] = ElevenLabsTTS()
            elif provider_type == "openai":
                self.providers[provider_type] = OpenAITTS()
            elif provider_type == "edge":
                self.providers[provider_type] = EdgeTTSProvider()
            else:
                self.providers[provider_type] = BrowserTTSProvider()
        
        self.current_provider = self.providers[provider_type]
        return self.current_provider
    
    async def synthesize(self, text: str, provider: str = None, **kwargs) -> bytes:
        """合成语音"""
        provider_obj = self.get_provider(provider)
        return await provider_obj.synthesize(text, **kwargs)
    
    def clean_text_for_tts(self, text: str) -> str:
        """清理文本以适合TTS"""
        import re
        
        # 移除代码块
        text = re.sub(r'```[\s\S]*?```', '', text)
        
        # 移除行内代码
        text = re.sub(r'`[^`]+`', '', text)
        
        # 移除Markdown链接，保留文字
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # 移除图片
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        
        # 移除推理标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    async def close(self):
        """关闭所有连接"""
        for provider in self.providers.values():
            await provider.close()
