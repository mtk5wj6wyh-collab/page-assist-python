"""
设置页面
"""
import streamlit as st
from pathlib import Path

from config import settings, AI_PROVIDERS, SEARCH_PROVIDERS, TTS_PROVIDERS
from utils.config_store import save_config

# .env 文件路径 — 项目根目录（兼容旧格式）
ENV_FILE = str(Path(__file__).parent.parent / ".env")


def _save_env(key: str, value):
    """写入一个环境变量到持久化存储，并同步更新内存中的 settings 对象"""
    save_config({key: str(value)})
    _sync_to_settings(key, value)


def _sync_to_settings(key: str, value):
    """将环境变量值同步到 settings 对象属性"""
    mapping = {
        "AI__OLLAMA_BASE_URL": ("ai", "ollama_base_url"),
        "AI__OLLAMA_MODEL": ("ai", "ollama_model"),
        "AI__OPENAI_API_KEY": ("ai", "openai_api_key"),
        "AI__OPENAI_BASE_URL": ("ai", "openai_base_url"),
        "AI__OPENAI_MODEL": ("ai", "openai_model"),
        "AI__ANTHROPIC_API_KEY": ("ai", "anthropic_api_key"),
        "AI__ANTHROPIC_MODEL": ("ai", "anthropic_model"),
        "AI__GOOGLE_API_KEY": ("ai", "google_api_key"),
        "AI__GOOGLE_MODEL": ("ai", "google_model"),
        "AI__GROQ_API_KEY": ("ai", "groq_api_key"),
        "AI__DEEPSEEK_API_KEY": ("ai", "deepseek_api_key"),
        "AI__MISTRAL_API_KEY": ("ai", "mistral_api_key"),
        "AI__MOONSHOT_API_KEY": ("ai", "moonshot_api_key"),
        "AI__DEFAULT_PROVIDER": ("ai", "default_provider"),
        "SEARCH__SEARCH_ENABLED": ("search", "search_enabled"),
        "SEARCH__SEARCH_PROVIDER": ("search", "search_provider"),
        "SEARCH__TAVILY_API_KEY": ("search", "tavily_api_key"),
        "SEARCH__BRAVE_API_KEY": ("search", "brave_api_key"),
        "SEARCH__SEARXNG_URL": ("search", "searxng_url"),
        "SEARCH__SEARCH_RESULT_COUNT": ("search", "search_result_count"),
        "TTS__TTS_ENABLED": ("tts", "tts_enabled"),
        "TTS__TTS_PROVIDER": ("tts", "tts_provider"),
        "TTS__ELEVENLABS_API_KEY": ("tts", "elevenlabs_api_key"),
        "TTS__ELEVENLABS_VOICE_ID": ("tts", "elevenlabs_voice_id"),
        "TTS__OPENAI_TTS_MODEL": ("tts", "openai_tts_model"),
        "TTS__OPENAI_TTS_VOICE": ("tts", "openai_tts_voice"),
        "TTS__EDGE_TTS_VOICE": ("tts", "edge_tts_voice"),
        "TTS__TTS_SPEED": ("tts", "tts_speed"),
        "UI__THEME": ("ui", "theme"),
        "UI__FONT_SIZE": ("ui", "font_size"),
        "UI__SIDEBAR_WIDTH": ("ui", "sidebar_width"),
        "UI__SHOW_USER_BUBBLE": ("ui", "show_user_bubble"),
        "UI__AUTO_COPY_RESPONSE": ("ui", "auto_copy_response"),
        "UI__RESTORE_LAST_CHAT": ("ui", "restore_last_chat"),
    }
    if key in mapping:
        section, attr = mapping[key]
        parent = getattr(settings, section)
        old_val = getattr(parent, attr)
        if isinstance(old_val, bool):
            value = str(value).lower() in ("true", "1", "yes")
        elif isinstance(old_val, int):
            value = int(value)
        elif isinstance(old_val, float):
            value = float(value)
        setattr(parent, attr, value)


def _get_st(key: str, default=""):
    """安全地从 st.session_state 获取值"""
    return st.session_state.get(key, default)


def render_settings_page():
    """渲染设置页面"""
    st.set_page_config(
        page_title=f"设置 - {settings.app_name}",
        page_icon="⚙️",
        layout="wide"
    )

    st.title("⚙️ 设置")

    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "AI提供商",
        "搜索设置",
        "语音设置",
        "界面设置",
        "快捷键"
    ])

    with tab1:
        st.subheader("AI提供商配置")

        # Ollama设置
        with st.expander("🖥️ Ollama (本地)", expanded=True):
            ollama_url = st.text_input(
                "服务器地址",
                value=settings.ai.ollama_base_url,
                help="Ollama服务地址",
                key="ollama_url"
            )
            ollama_model = st.text_input(
                "默认模型",
                value=settings.ai.ollama_model,
                help="Ollama模型名称",
                key="ollama_model"
            )

            if st.button("测试连接", key="test_ollama"):
                st.info("连接测试功能需要后端服务支持")

        # OpenAI设置
        with st.expander("🌐 OpenAI"):
            openai_key = st.text_input(
                "API Key",
                value=settings.ai.openai_api_key or "",
                type="password",
                help="OpenAI API密钥",
                key="openai_api_key"
            )
            openai_url = st.text_input(
                "API地址",
                value=settings.ai.openai_base_url,
                help="OpenAI API端点",
                key="openai_base_url"
            )
            openai_model = st.selectbox(
                "默认模型",
                AI_PROVIDERS.get("openai", {}).get("models", ["gpt-4"]),
                key="openai_model"
            )

        # Anthropic设置
        with st.expander("🧠 Anthropic (Claude)"):
            anthropic_key = st.text_input(
                "API Key",
                value=settings.ai.anthropic_api_key or "",
                type="password",
                key="anthropic_api_key"
            )
            anthropic_model = st.selectbox(
                "默认模型",
                AI_PROVIDERS.get("anthropic", {}).get("models", ["claude-3-sonnet-20240229"]),
                key="anthropic_model"
            )

        # Google设置
        with st.expander("🔵 Google Gemini"):
            google_key = st.text_input(
                "API Key",
                value=settings.ai.google_api_key or "",
                type="password",
                key="google_api_key"
            )
            google_model = st.selectbox(
                "默认模型",
                AI_PROVIDERS.get("google", {}).get("models", ["gemini-pro"]),
                key="google_model"
            )

        # 其他提供商
        with st.expander("📦 其他提供商"):
            groq_key = st.text_input("Groq API Key", value=settings.ai.groq_api_key or "", type="password", key="groq_key")
            deepseek_key = st.text_input("DeepSeek API Key", value=settings.ai.deepseek_api_key or "", type="password", key="deepseek_key")
            mistral_key = st.text_input("Mistral API Key", value=settings.ai.mistral_api_key or "", type="password", key="mistral_key")
            moonshot_key = st.text_input("Moonshot API Key", value=settings.ai.moonshot_api_key or "", type="password", key="moonshot_key")

        # 默认提供商
        st.divider()
        default_provider = st.selectbox(
            "默认AI提供商",
            list(AI_PROVIDERS.keys()),
            index=list(AI_PROVIDERS.keys()).index(settings.ai.default_provider) if settings.ai.default_provider in AI_PROVIDERS else 0,
            key="default_provider"
        )

        if st.button("保存AI设置", key="save_ai"):
            _save_env("AI__OLLAMA_BASE_URL", _get_st("ollama_url", settings.ai.ollama_base_url))
            _save_env("AI__OLLAMA_MODEL", _get_st("ollama_model", settings.ai.ollama_model))
            _save_env("AI__OPENAI_API_KEY", _get_st("openai_api_key", ""))
            _save_env("AI__OPENAI_BASE_URL", _get_st("openai_base_url", settings.ai.openai_base_url))
            _save_env("AI__OPENAI_MODEL", _get_st("openai_model", settings.ai.openai_model))
            _save_env("AI__ANTHROPIC_API_KEY", _get_st("anthropic_api_key", ""))
            _save_env("AI__ANTHROPIC_MODEL", _get_st("anthropic_model", settings.ai.anthropic_model))
            _save_env("AI__GOOGLE_API_KEY", _get_st("google_api_key", ""))
            _save_env("AI__GOOGLE_MODEL", _get_st("google_model", settings.ai.google_model))
            _save_env("AI__GROQ_API_KEY", _get_st("groq_key", ""))
            _save_env("AI__DEEPSEEK_API_KEY", _get_st("deepseek_key", ""))
            _save_env("AI__MISTRAL_API_KEY", _get_st("mistral_key", ""))
            _save_env("AI__MOONSHOT_API_KEY", _get_st("moonshot_key", ""))
            _save_env("AI__DEFAULT_PROVIDER", _get_st("default_provider", settings.ai.default_provider))
            st.success("✅ AI 设置已保存到 .env 文件")

    with tab2:
        st.subheader("搜索功能设置")

        search_enabled = st.toggle("启用搜索", value=settings.search.search_enabled, key="search_enabled")

        if search_enabled:
            search_provider = st.selectbox(
                "搜索提供商",
                list(SEARCH_PROVIDERS.keys()),
                format_func=lambda x: SEARCH_PROVIDERS[x]["name"],
                key="search_provider"
            )

            if search_provider == "tavily":
                tavily_key = st.text_input(
                    "Tavily API Key",
                    value=settings.search.tavily_api_key or "",
                    type="password",
                    key="tavily_key"
                )
            elif search_provider == "brave":
                brave_key = st.text_input(
                    "Brave Search API Key",
                    value=settings.search.brave_api_key or "",
                    type="password",
                    key="brave_key"
                )
            elif search_provider == "searxng":
                searxng_url = st.text_input(
                    "SearXNG地址",
                    value=settings.search.searxng_url,
                    key="searxng_url"
                )

            search_count = st.slider(
                "搜索结果数量",
                1, 20,
                value=settings.search.search_result_count,
                key="search_count"
            )

        if st.button("保存搜索设置", key="save_search"):
            _save_env("SEARCH__SEARCH_ENABLED", _get_st("search_enabled", False))
            _save_env("SEARCH__SEARCH_PROVIDER", _get_st("search_provider", "duckduckgo"))
            _save_env("SEARCH__TAVILY_API_KEY", _get_st("tavily_key", ""))
            _save_env("SEARCH__BRAVE_API_KEY", _get_st("brave_key", ""))
            _save_env("SEARCH__SEARXNG_URL", _get_st("searxng_url", settings.search.searxng_url))
            _save_env("SEARCH__SEARCH_RESULT_COUNT", _get_st("search_count", 5))
            st.success("✅ 搜索设置已保存到 .env 文件")

    with tab3:
        st.subheader("语音设置")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### TTS 语音合成")
            tts_enabled = st.toggle("启用TTS", value=settings.tts.tts_enabled, key="tts_enabled")

            if tts_enabled:
                tts_provider = st.selectbox(
                    "TTS提供商",
                    list(TTS_PROVIDERS.keys()),
                    format_func=lambda x: TTS_PROVIDERS[x]["name"],
                    key="tts_provider"
                )

                if tts_provider == "elevenlabs":
                    elevenlabs_key = st.text_input(
                        "ElevenLabs API Key",
                        value=settings.tts.elevenlabs_api_key or "",
                        type="password",
                        key="elevenlabs_key"
                    )
                    voice_id = st.text_input(
                        "Voice ID",
                        value=settings.tts.elevenlabs_voice_id,
                        key="elevenlabs_voice_id"
                    )
                elif tts_provider == "openai":
                    openai_tts_model = st.selectbox(
                        "模型",
                        TTS_PROVIDERS["openai"].get("models", ["tts-1"]),
                        key="openai_tts_model"
                    )
                    openai_voice = st.selectbox(
                        "声音",
                        TTS_PROVIDERS["openai"].get("voices", ["alloy"]),
                        key="openai_tts_voice"
                    )
                elif tts_provider == "edge":
                    edge_voice = st.selectbox(
                        "声音",
                        TTS_PROVIDERS["edge"].get("voices", ["zh-CN-XiaoxiaoNeural"]),
                        key="edge_tts_voice"
                    )

                tts_speed = st.slider(
                    "语速",
                    0.5, 2.0,
                    value=settings.tts.tts_speed,
                    key="tts_speed"
                )

        with col2:
            st.markdown("### STT 语音识别")
            stt_enabled = st.toggle("启用STT", value=settings.stt.stt_enabled, key="stt_enabled")

            if stt_enabled:
                st.info("语音识别将在聊天界面提供麦克风按钮")

        if st.button("保存语音设置", key="save_voice"):
            _save_env("TTS__TTS_ENABLED", _get_st("tts_enabled", False))
            _save_env("TTS__TTS_PROVIDER", _get_st("tts_provider", "browser"))
            _save_env("TTS__ELEVENLABS_API_KEY", _get_st("elevenlabs_key", ""))
            _save_env("TTS__ELEVENLABS_VOICE_ID", _get_st("elevenlabs_voice_id", settings.tts.elevenlabs_voice_id))
            _save_env("TTS__OPENAI_TTS_MODEL", _get_st("openai_tts_model", "tts-1"))
            _save_env("TTS__OPENAI_TTS_VOICE", _get_st("openai_tts_voice", "alloy"))
            _save_env("TTS__EDGE_TTS_VOICE", _get_st("edge_tts_voice", "zh-CN-XiaoxiaoNeural"))
            _save_env("TTS__TTS_SPEED", _get_st("tts_speed", 1.0))
            _save_env("STT__STT_ENABLED", _get_st("stt_enabled", False))
            st.success("✅ 语音设置已保存到 .env 文件")

    with tab4:
        st.subheader("界面设置")

        theme = st.selectbox(
            "主题",
            ["dark", "light", "system"],
            index=["dark", "light", "system"].index(settings.ui.theme),
            key="ui_theme"
        )

        font_size = st.selectbox(
            "字体大小",
            ["small", "medium", "large"],
            index=["small", "medium", "large"].index(settings.ui.font_size),
            key="ui_font_size"
        )

        sidebar_width = st.selectbox(
            "侧边栏宽度",
            ["narrow", "medium", "wide"],
            index=["narrow", "medium", "wide"].index(settings.ui.sidebar_width),
            key="ui_sidebar_width"
        )

        show_user_bubble = st.toggle(
            "显示用户气泡",
            value=settings.ui.show_user_bubble,
            key="show_user_bubble"
        )

        auto_copy = st.toggle(
            "自动复制AI响应",
            value=settings.ui.auto_copy_response,
            key="auto_copy"
        )

        restore_chat = st.toggle(
            "恢复上次对话",
            value=settings.ui.restore_last_chat,
            key="restore_chat"
        )

        if st.button("保存界面设置", key="save_ui"):
            _save_env("UI__THEME", _get_st("ui_theme", "dark"))
            _save_env("UI__FONT_SIZE", _get_st("ui_font_size", "medium"))
            _save_env("UI__SIDEBAR_WIDTH", _get_st("ui_sidebar_width", "medium"))
            _save_env("UI__SHOW_USER_BUBBLE", _get_st("show_user_bubble", True))
            _save_env("UI__AUTO_COPY_RESPONSE", _get_st("auto_copy", False))
            _save_env("UI__RESTORE_LAST_CHAT", _get_st("restore_chat", True))
            st.success("✅ 界面设置已保存到 .env 文件")

    with tab5:
        st.subheader("快捷键设置")

        st.write("当前快捷键配置：")

        hotkeys = settings.hotkeys

        for action, key in hotkeys.items():
            col1, col2 = st.columns([2, 1])
            with col1:
                st.text_input(
                    action.replace("_", " ").title(),
                    value=key,
                    disabled=True,
                    key=f"hotkey_{action}"
                )
            with col2:
                st.write("")  # 占位

        st.divider()
        st.info("快捷键功能需要前端JavaScript实现")


if __name__ == "__main__":
    render_settings_page()
