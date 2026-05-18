"""
聊天页面 — 对话持久化到 SQLite 数据库
"""
import asyncio
import uuid
import streamlit as st
from datetime import datetime

from config import settings, AI_PROVIDERS
from services.ai_provider import AIProviderFactory
from services.search import SearchService
from database import init_db, get_db_context
from services.chat_manager import ChatManager


# ── 同步包装：Streamlit 中调用异步 DB ─────────────────────

def _db_init():
    """初始化数据库表"""
    try:
        asyncio.run(init_db())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_db())


def _db_list_sessions():
    """从 DB 读取所有会话"""
    async def _run():
        async with get_db_context() as db:
            cm = ChatManager(db)
            return await cm.get_sessions()
    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())


def _db_get_messages(session_id: str):
    """从 DB 读取会话消息"""
    async def _run():
        async with get_db_context() as db:
            cm = ChatManager(db)
            return await cm.get_messages(session_id)
    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())


def _db_create_session(provider: str, model: str):
    """在 DB 中新建会话"""
    async def _run():
        async with get_db_context() as db:
            cm = ChatManager(db)
            return await cm.create_session(
                title="新对话",
                provider=provider,
                model=model,
            )
    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())


def _db_add_message(session_id: str, role: str, content: str, model: str = None):
    """向 DB 添加消息"""
    async def _run():
        async with get_db_context() as db:
            cm = ChatManager(db)
            return await cm.add_message(session_id, role, content, model=model)
    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())


def _db_delete_session(session_id: str):
    """删除 DB 中的会话"""
    async def _run():
        async with get_db_context() as db:
            cm = ChatManager(db)
            return await cm.delete_session(session_id)
    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())


def _db_update_session(session_id: str, title: str):
    """更新会话标题"""
    async def _run():
        async with get_db_context() as db:
            cm = ChatManager(db)
            return await cm.update_session(session_id, title=title)
    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())


# ── 辅助函数 ────────────────────────────────────────

_API_KEY_PROVIDERS = {
    "openai": ("openai_api_key", "OpenAI"),
    "deepseek": ("deepseek_api_key", "DeepSeek"),
    "mistral": ("mistral_api_key", "Mistral"),
    "moonshot": ("moonshot_api_key", "Moonshot"),
    "anthropic": ("anthropic_api_key", "Anthropic"),
    "google": ("google_api_key", "Google Gemini"),
    "groq": ("groq_api_key", "Groq"),
}


def _check_provider_ready(provider_type):
    if provider_type == "ollama":
        return None
    info = _API_KEY_PROVIDERS.get(provider_type)
    if info:
        attr, name = info
        key = getattr(settings.ai, attr, None)
        if not key:
            return (
                f"⚠️ **{name}** 未配置 API Key\n\n"
                f"请前往 **设置 → AI提供商** 填写并保存 "
                f"`{name}` 的 API Key，然后重试。"
            )
    return None


def _build_messages(session_messages):
    messages = []
    for msg in session_messages:
        if msg["role"] in ("user", "assistant", "system"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def _get_title(messages):
    """根据第一条用户消息生成标题"""
    for m in messages:
        if m["role"] == "user":
            text = m["content"].strip()
            return text[:20] + ("..." if len(text) > 20 else "")
    return "新对话"


def _call_ai(prompt, session_messages, provider_type, model_name, enable_search=False):
    err = _check_provider_ready(provider_type)
    if err:
        return err
    provider = None
    try:
        factory = AIProviderFactory()
        provider = factory.create(provider_type)
        messages = _build_messages(session_messages)
        if not messages or messages[-1].get("content") != prompt:
            messages.append({"role": "user", "content": prompt})
        if enable_search and settings.search.search_enabled:
            search_service = SearchService()
            search_context = asyncio.run(
                search_service.search_with_context(prompt, num_results=5)
            )
            now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
            messages.insert(0, {
                "role": "system",
                "content": f"当前日期时间：{now}\n\n以下是网络搜索结果，请基于这些信息回答问题：\n\n{search_context}"
            })
        response = asyncio.run(provider.chat(messages, model=model_name))
        return response
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "Authorization" in err_str or "Unauthorized" in err_str:
            return (
                f"⚠️ **{provider_type} 认证失败**\n\n"
                f"API Key 无效或未配置。请前往 **设置 → AI提供商** 检查并重新保存 "
                f"`{provider_type}` 的 API Key，然后重试。\n\n"
                f"技术详情: `{err_str[:200]}`"
            )
        return f"⚠️ 调用 AI 时出错: {err_str}"
    finally:
        if provider:
            try:
                asyncio.run(provider.close())
            except Exception:
                pass


# ── 主渲染函数 ─────────────────────────────────────

def render_chat_page():
    """渲染聊天页面"""
    st.set_page_config(
        page_title=f"聊天 - {settings.app_name}",
        page_icon="💬",
        layout="wide"
    )

    # 首次加载时初始化数据库表
    if "db_inited" not in st.session_state:
        _db_init()
        st.session_state.db_inited = True

    # 从 DB 获取会话列表，构建 {sid: {title, updated_at}}
    if "db_sessions" not in st.session_state:
        sessions = _db_list_sessions()
        st.session_state.db_sessions = {
            s.id: {"title": s.title, "updated_at": s.updated_at}
            for s in sessions
        }
        st.session_state.current_session_id = None

    # 自动选择最新会话或新建
    cid = st.session_state.current_session_id
    if not cid or cid not in st.session_state.db_sessions:
        if st.session_state.db_sessions:
            cid = sorted(st.session_state.db_sessions.keys(),
                         key=lambda k: st.session_state.db_sessions[k]["updated_at"],
                         reverse=True)[0]
        else:
            # 首次无会话 → 新建
            s = _db_create_session(settings.ai.default_provider, settings.ai.ollama_model)
            st.session_state.db_sessions[s.id] = {"title": s.title, "updated_at": s.updated_at}
            cid = s.id
        st.session_state.current_session_id = cid

    # 加载当前会话消息
    cid = st.session_state.current_session_id
    if st.session_state.get("_loaded_session") != cid:
        msgs = _db_get_messages(cid)
        st.session_state.messages = [
            {"role": m.role, "content": m.content,
             "time": m.created_at.strftime("%H:%M:%S") if m.created_at else ""}
            for m in msgs
        ]
        st.session_state._loaded_session = cid

    if "provider" not in st.session_state:
        st.session_state.provider = settings.ai.default_provider
    if "model" not in st.session_state:
        st.session_state.model = settings.ai.ollama_model
    if "enable_search" not in st.session_state:
        st.session_state.enable_search = False

    # ═══════════════ 侧边栏 ═══════════════
    with st.sidebar:
        st.title("历史对话")

        if st.button("新建对话", use_container_width=True):
            s = _db_create_session(st.session_state.provider, st.session_state.model)
            st.session_state.db_sessions[s.id] = {"title": s.title, "updated_at": s.updated_at}
            st.session_state.current_session_id = s.id
            st.session_state.messages = []
            st.session_state._loaded_session = s.id
            st.rerun()

        # 会话列表
        sorted_ids = sorted(st.session_state.db_sessions.keys(),
                            key=lambda k: st.session_state.db_sessions[k]["updated_at"],
                            reverse=True)
        for sid in sorted_ids:
            info = st.session_state.db_sessions[sid]
            title = info["title"]
            active = "🔵" if sid == cid else "  "
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(f"{active} {title}", key=f"sid_{sid}",
                             use_container_width=True):
                    st.session_state.current_session_id = sid
                    st.session_state._loaded_session = None  # 触发重载
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{sid}"):
                    _db_delete_session(sid)
                    st.session_state.db_sessions.pop(sid, None)
                    if sid == cid:
                        remaining = list(st.session_state.db_sessions.keys())
                        if remaining:
                            st.session_state.current_session_id = remaining[0]
                        else:
                            s = _db_create_session(st.session_state.provider,
                                                   st.session_state.model)
                            st.session_state.db_sessions[s.id] = {
                                "title": s.title, "updated_at": s.updated_at}
                            st.session_state.current_session_id = s.id
                        st.session_state._loaded_session = None
                    st.rerun()

        st.divider()

        provider_options = list(AI_PROVIDERS.keys())
        selected_provider = st.selectbox(
            "AI提供商", provider_options,
            index=provider_options.index(st.session_state.provider)
            if st.session_state.provider in provider_options else 0
        )
        st.session_state.provider = selected_provider

        models = AI_PROVIDERS.get(selected_provider, {}).get("models", [])
        if models:
            selected_model = st.selectbox("模型", models)
            st.session_state.model = selected_model

        st.divider()

        search_toggle = st.toggle(
            "🔍 联网搜索",
            value=st.session_state.enable_search,
            help="开启后 AI 会先搜索网络再回答"
        )
        st.session_state.enable_search = search_toggle
        if search_toggle and not settings.search.search_enabled:
            st.caption("⚠️ 请在设置中启用搜索功能")
        elif search_toggle:
            st.caption(f"🌐 {settings.search.search_provider}")

    # ═══════════════ 聊天主区域 ═══════════════
    st.title("💬 " + settings.app_name)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "time" in message:
                st.caption(message["time"])

    if prompt := st.chat_input("输入消息..."):

        cid = st.session_state.current_session_id

        # 保存用户消息到 DB
        _db_add_message(cid, "user", prompt)

        st.session_state.messages.append({
            "role": "user", "content": prompt,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 回复
        with st.chat_message("assistant"):
            with st.spinner(f"🤔 {st.session_state.provider} "
                            f"{'🌐' if st.session_state.enable_search else ''} 思考中..."):
                response = _call_ai(
                    prompt=prompt,
                    session_messages=st.session_state.messages,
                    provider_type=st.session_state.provider,
                    model_name=st.session_state.model,
                    enable_search=st.session_state.enable_search
                )
                st.markdown(response)
                st.session_state.messages.append({
                    "role": "assistant", "content": response,
                    "time": datetime.now().strftime("%H:%M:%S")
                })

        # 保存 AI 回复到 DB
        _db_add_message(cid, "assistant", response, model=st.session_state.model)

        # 更新会话标题（以第一条用户消息命名）
        title = _get_title(st.session_state.messages)
        _db_update_session(cid, title)
        st.session_state.db_sessions[cid]["title"] = title
        st.session_state.db_sessions[cid]["updated_at"] = datetime.now()

        st.rerun()


if __name__ == "__main__":
    render_chat_page()
