"""
Page Assist - Python Edition 主应用入口
Streamlit 多页面应用
"""
import sys
from pathlib import Path

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from config import settings

# 设置页面配置
st.set_page_config(
    page_title=settings.app_name,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """主应用入口"""
    
    # 侧边栏
    with st.sidebar:
        st.title(f"🤖 {settings.app_name}")
        st.caption(f"版本 {settings.app_version}")
        
        st.divider()
        
        # 导航菜单 - 使用 pages/ 下的文件名
        st.page_link("pages/01_聊天.py", label="💬 聊天", icon="💬")
        st.page_link("pages/02_知识库.py", label="📚 知识库", icon="📚")
        st.page_link("pages/03_提示词.py", label="📝 提示词", icon="📝")
        st.page_link("pages/05_工具.py", label="🛠️ 工具", icon="🛠️")
        
        st.divider()
        st.page_link("pages/04_设置.py", label="⚙️ 设置", icon="⚙️")
        
        st.divider()
        
        # 状态信息
        st.caption("状态")
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            st.markdown("**AI提供商**")
            st.caption(settings.ai.default_provider)
        with status_col2:
            st.markdown("**主题**")
            st.caption(settings.ui.theme)
        
        # 底部信息
        st.divider()
        st.caption("Page Assist - Python Edition")
        st.caption("基于本地AI模型的Web UI助手")
    
    # 主内容区
    st.title(f"欢迎使用 {settings.app_name} 🤖")
    
    # 快速开始卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info("💬")
        st.markdown("### 开始聊天")
        st.write("与AI助手对话")
        if st.button("新建对话", key="quick_new_chat"):
            st.switch_page("pages/01_聊天.py")
    
    with col2:
        st.success("📚")
        st.markdown("### 知识库")
        st.write("管理文档知识")
        if st.button("管理知识库", key="quick_knowledge"):
            st.switch_page("pages/02_知识库.py")
    
    with col3:
        st.warning("📝")
        st.markdown("### 提示词")
        st.write("自定义AI行为")
        if st.button("管理提示词", key="quick_prompts"):
            st.switch_page("pages/03_提示词.py")
    
    with col4:
        st.error("🛠️")
        st.markdown("### 工具箱")
        st.write("扩展功能")
        if st.button("打开工具", key="quick_tools"):
            st.switch_page("pages/05_工具.py")
    
    st.divider()
    
    # 功能介绍
    st.markdown("## 功能特点")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🤖 多AI支持
        - **Ollama** - 本地运行的开源模型
        - **OpenAI** - GPT-4、GPT-3.5
        - **Anthropic** - Claude系列
        - **Google** - Gemini模型
        - **更多** - Groq、DeepSeek等
        """)
        
        st.markdown("""
        ### 📚 RAG知识库
        - 上传PDF、Word、文本文件
        - 智能文档分块
        - 向量检索增强
        - 本地私有部署
        """)
    
    with col2:
        st.markdown("""
        ### 🔍 网络搜索
        - DuckDuckGo
        - Tavily AI
        - Brave Search
        - SearXNG自托管
        """)
        
        st.markdown("""
        ### 🗣️ 语音功能
        - TTS语音合成
        - STT语音识别
        - 多语音选择
        """)
    
    st.divider()
    
    # 最近对话
    st.markdown("## 最近对话")
    
    if "recent_chats" not in st.session_state:
        st.session_state.recent_chats = [
            {"title": "Python编程问题", "time": "5分钟前"},
            {"title": "翻译一段英文", "time": "1小时前"},
            {"title": "代码审查", "time": "2小时前"},
        ]
    
    for chat in st.session_state.recent_chats:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.button(f"💬 {chat['title']}", key=f"chat_{chat['title']}")
        with col2:
            st.caption(chat["time"])
        with col3:
            st.button("🗑️", key=f"del_{chat['title']}")
    
    if not st.session_state.recent_chats:
        st.info("暂无对话记录，开始聊天吧！")


if __name__ == "__main__":
    main()
