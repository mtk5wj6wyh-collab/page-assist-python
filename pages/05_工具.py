"""
工具页面 — 实用小工具集合
"""
import asyncio
import json
import streamlit as st
from pathlib import Path
from datetime import datetime
from config import settings, DATA_DIR
from services.rag import PDFProcessor, TextProcessor, DocxProcessor, HtmlProcessor
from services.search import SearchService


def process_document(uploaded_file):
    """处理上传的文档并提取文本"""
    suffix = Path(uploaded_file.name).suffix.lower().lstrip(".")
    processors = {
        "pdf": PDFProcessor(), "txt": TextProcessor(), "md": TextProcessor(),
        "csv": TextProcessor(), "json": TextProcessor(),
        "docx": DocxProcessor(), "doc": DocxProcessor(),
        "html": HtmlProcessor(), "htm": HtmlProcessor(),
    }
    processor = processors.get(suffix)
    if not processor:
        return None, f"不支持的文件类型: .{suffix}"
    tmp_dir = DATA_DIR / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / uploaded_file.name
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    try:
        chunks = asyncio.run(processor.process(str(tmp_path)))
        return chunks, None
    except Exception as e:
        return None, f"处理失败: {str(e)}"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def render_tools_page():
    """渲染工具页面"""
    st.set_page_config(
        page_title=f"工具 - {settings.app_name}",
        page_icon="🛠️",
        layout="wide"
    )
    st.title("🛠️ 工具箱")

    # ========== 第一行 ==========
    col1, col2, col3 = st.columns(3)

    # ----- 1. 文档处理 -----
    with col1:
        st.markdown("### 📄 文档处理")
        uploaded = st.file_uploader(
            "上传文件提取文字",
            type=["pdf", "txt", "md", "docx", "html", "csv"],
            key="tool_doc_upload",
            label_visibility="collapsed",
        )
        if uploaded:
            with st.spinner("⏳ 正在提取..."):
                chunks, err = process_document(uploaded)
            if err:
                st.error(err)
            elif chunks:
                valid = [c for c in chunks if c.strip()]
                st.success(f"✅ 提取完成，共 {len(chunks)} 段，{sum(len(c) for c in valid)} 字")
                full_text = "\n\n".join(c for c in valid)
                tab_preview, tab_dl = st.tabs(["📖 预览", "📥 下载"])
                with tab_preview:
                    st.text_area("提取内容", full_text[:3000], height=250,
                                 label_visibility="collapsed")
                with tab_dl:
                    st.download_button(
                        "📥 下载为 .txt",
                        full_text,
                        file_name=f"{Path(uploaded.name).stem}_提取.txt",
                        use_container_width=True,
                    )

    # ----- 2. 网络搜索 -----
    with col2:
        st.markdown("### 🔍 网络搜索")
        q = st.text_input("搜索关键词", key="tool_search_q", label_visibility="collapsed",
                          placeholder="输入关键词回车搜索")
        if q:
            with st.spinner("⏳ 搜索中..."):
                try:
                    svc = SearchService()
                    results = asyncio.run(svc.search(q, num_results=5))
                    if results and "error" not in results[0]:
                        for i, r in enumerate(results, 1):
                            st.markdown(
                                f"**{i}. [{r['title']}]({r['url']})**  \n"
                                f"{r['snippet'][:200]}", unsafe_allow_html=True
                            )
                    else:
                        st.info("未找到结果")
                except Exception as e:
                    st.error(f"搜索失败: {e}")

    # ----- 3. 快捷短语 -----
    with col3:
        st.markdown("### ⚡ 快捷短语")
        phrases = [
            ("🤔 解释代码", "请解释以下代码："),
            ("📝 总结内容", "请总结以下内容："),
            ("🌍 翻译中文", "请翻译成中文："),
            ("✏️ 改进文本", "请改进这段文本："),
        ]
        for label, text in phrases:
            if st.button(label, key=f"qp_{label}", use_container_width=True):
                st.session_state["quick_phrase"] = text
                st.toast(f"已复制: {text}")

        if st.session_state.get("quick_phrase"):
            st.code(st.session_state["quick_phrase"], language="text")
            st.page_link("pages/01_聊天.py", label="💬 去聊天粘贴使用", icon="💬")

    # ========== 第二行 ==========
    st.divider()
    col1, col2, col3 = st.columns(3)

    # ----- 4. 导出聊天 -----
    with col1:
        st.markdown("### 💬 导出聊天")
        msgs = st.session_state.get("messages", [])
        st.caption(f"当前会话共 {len(msgs)} 条消息")
        if msgs:
            md_content = ""
            for m in msgs:
                role = "👤 用户" if m["role"] == "user" else "🤖 AI"
                md_content += f"### {role} ({m.get('time','')})\n{m['content']}\n\n"
            export_name = f"聊天记录_{datetime.now().strftime('%Y%m%d_%H%M')}"
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button("📥 导出 .md", md_content,
                                   file_name=f"{export_name}.md", use_container_width=True)
            with col_b:
                st.download_button("📥 导出 .json",
                                   json.dumps(msgs, ensure_ascii=False, indent=2),
                                   file_name=f"{export_name}.json", use_container_width=True)
        else:
            st.info("暂无聊天记录")

    # ----- 5. 文件编码转换 -----
    with col2:
        st.markdown("### 🔄 文本工具")
        text_in = st.text_area("输入文本", height=100, key="tool_text",
                               placeholder="粘贴文本，查看字数统计...")
        if text_in:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("字数", f"{len(text_in)}")
            with col_b:
                st.metric("字符", f"{len(text_in.encode('utf-8'))} B")
            with col_c:
                lines = [l for l in text_in.split("\n") if l.strip()]
                st.metric("行数", f"{len(lines)}")
            st.button("📋 复制", on_click=lambda: st.toast("已复制到剪贴板"),
                      key="tool_copy_text")

    # ----- 6. 系统状态 -----
    with col3:
        st.markdown("### 🖥️ 系统状态")
        st.metric("默认 AI", settings.ai.default_provider)
        st.metric("搜索源", settings.search.search_provider,
                  delta="已启用" if settings.search.search_enabled else None)
        st.metric("数据库", "SQLite", delta=Path(DATA_DIR / "page_assist.db").exists() and "已就绪" or "未初始化")
        if st.button("刷新", key="tool_status_refresh", use_container_width=True):
            st.rerun()


if __name__ == "__main__":
    render_tools_page()
