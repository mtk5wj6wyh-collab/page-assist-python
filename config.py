"""
配置管理模块
管理所有配置选项
"""
import os
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


# 项目根目录
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库路径
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/page_assist.db"

# 从持久化存储加载配置到 os.environ
from utils.config_store import load_config
load_config()

# 手动加载 .env 到 os.environ（兼容旧格式）
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE, override=True)


class AIProviderSettings(BaseModel):
    """AI提供商配置"""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"
    azure_openai_key: Optional[str] = None
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    google_api_key: Optional[str] = None
    google_model: str = "gemini-pro"
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "mixtral-8x7b-32768"
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    mistral_api_key: Optional[str] = None
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-large-latest"
    moonshot_api_key: Optional[str] = None
    moonshot_base_url: str = "https://api.moonshot.cn/v1"
    moonshot_model: str = "moonshot-v1-8k"
    mimo_api_key: Optional[str] = None
    mimo_base_url: str = "https://api.xiaomimimo.com/v1"
    mimo_model: str = "mimo-v2.5-pro"
    default_provider: str = "ollama"


class SearchSettings(BaseModel):
    """搜索功能配置"""
    search_enabled: bool = False
    search_provider: str = "bing"
    tavily_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    searxng_url: str = "http://localhost:8888"
    search_result_count: int = 5


class TTSSettings(BaseModel):
    """TTS语音合成配置"""
    tts_enabled: bool = False
    tts_provider: str = "browser"
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"
    edge_tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_speed: float = 1.0
    tts_volume: float = 1.0


class STTSettings(BaseModel):
    """STT语音识别配置"""
    stt_enabled: bool = False
    stt_provider: str = "browser"
    whisper_api_url: Optional[str] = None


class RGBSettings(BaseModel):
    """RAG知识库配置"""
    rag_enabled: bool = True
    embedding_model: str = "nomic-embed-text"
    chunk_size: int = 500
    chunk_overlap: int = 100
    retrieval_top_k: int = 5


class UIsettings(BaseModel):
    """界面配置"""
    theme: str = "dark"
    font_size: str = "medium"
    sidebar_width: str = "medium"
    show_user_bubble: bool = True
    auto_copy_response: bool = False
    temporary_chat: bool = False
    restore_last_chat: bool = True


class Settings(BaseSettings):
    """全局设置"""
    app_name: str = "Page Assist"
    app_version: str = "1.0.0"
    ai: AIProviderSettings = Field(default_factory=AIProviderSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    stt: STTSettings = Field(default_factory=STTSettings)
    rag: RGBSettings = Field(default_factory=RGBSettings)
    ui: UIsettings = Field(default_factory=UIsettings)
    hotkeys: Dict[str, str] = {
        "new_chat": "Ctrl+Shift+N",
        "toggle_sidebar": "Ctrl+B",
        "focus_input": "Shift+Esc",
        "send_message": "Enter",
        "newline": "Shift+Enter",
    }

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore"
    )


settings = Settings()


AI_PROVIDERS = {
    "ollama": {"name": "Ollama", "models": [], "requires_local": True},
    "openai": {"name": "OpenAI", "models": ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"], "requires_api_key": True},
    "azure_openai": {"name": "Azure OpenAI", "models": ["gpt-4", "gpt-35-turbo"], "requires_api_key": True},
    "anthropic": {"name": "Anthropic", "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"], "requires_api_key": True},
    "google": {"name": "Google Gemini", "models": ["gemini-pro", "gemini-pro-vision"], "requires_api_key": True},
    "groq": {"name": "Groq", "models": ["mixtral-8x7b-32768", "llama2-70b-4096"], "requires_api_key": True},
    "deepseek": {"name": "DeepSeek", "models": ["deepseek-chat"], "requires_api_key": True},
    "mistral": {"name": "Mistral", "models": ["mistral-large-latest", "mistral-medium-latest"], "requires_api_key": True},
    "moonshot": {"name": "Moonshot (Kimi)", "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"], "requires_api_key": True},
    "mimo": {"name": "Xiaomi MiMo", "models": ["mimo-v2.5-pro", "mimo-v2-flash"], "requires_api_key": True},
}

SEARCH_PROVIDERS = {
    "bing": {"name": "Bing", "requires_api_key": False, "free": True},
    "duckduckgo": {"name": "DuckDuckGo", "requires_api_key": False, "free": True},
    "google": {"name": "Google", "requires_api_key": False, "free": True},
    "tavily": {"name": "Tavily", "requires_api_key": True},
    "brave": {"name": "Brave Search", "requires_api_key": True},
    "searxng": {"name": "SearXNG", "requires_api_key": False, "self_hosted": True},
}

TTS_PROVIDERS = {
    "browser": {"name": "浏览器TTS", "requires_api_key": False, "voices": []},
    "elevenlabs": {"name": "ElevenLabs", "requires_api_key": True, "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]},
    "openai": {"name": "OpenAI TTS", "requires_api_key": True, "models": ["tts-1", "tts-1-hd"], "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]},
    "edge": {"name": "Edge TTS", "requires_api_key": False, "voices": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "en-US-JennyNeural"]},
}

EMBEDDING_MODELS = {
    "ollama": {"nomic-embed-text": "Nomic Embed Text", "all-minilm": "All MiniLM", "bge-m3": "BGE M3", "mxbai-embed-large": "MXBAI Embed Large"},
    "openai": {"text-embedding-3-small": "OpenAI Embedding 3 Small", "text-embedding-3-large": "OpenAI Embedding 3 Large"},
}
