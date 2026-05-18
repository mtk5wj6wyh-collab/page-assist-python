"""
知识库管理页面
"""
import streamlit as st
import os
from datetime import datetime

from config import settings, EMBEDDING_MODELS


def render_knowledge_page():
    """渲染知识库页面"""
    st.set_page_config(
        page_title=f"知识库 - {settings.app_name}",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 知识库管理")
    
    # 初始化状态
    if "knowledge_bases" not in st.session_state:
        st.session_state.knowledge_bases = []
    
    if "documents" not in st.session_state:
        st.session_state.documents = []
    
    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["知识库列表", "上传文档", "检索测试"])
    
    with tab1:
        st.subheader("我的知识库")
        
        # 创建新知识库按钮
        if st.button("➕ 创建新知识库"):
            st.session_state.show_create_kb = True
        
        # 知识库列表
        if st.session_state.knowledge_bases:
            for kb in st.session_state.knowledge_bases:
                with st.expander(f"📁 {kb['name']}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"描述: {kb.get('description', '无')}")
                        st.write(f"文档数: {kb.get('doc_count', 0)}")
                        st.write(f"创建时间: {kb.get('created_at', '未知')}")
                    with col2:
                        if st.button("删除", key=f"del_{kb['id']}"):
                            st.session_state.knowledge_bases = [
                                k for k in st.session_state.knowledge_bases if k['id'] != kb['id']
                            ]
                            st.rerun()
        else:
            st.info("暂无知识库，点击上方按钮创建")
        
        # 创建知识库表单
        if st.session_state.get("show_create_kb", False):
            with st.form("create_kb_form"):
                kb_name = st.text_input("知识库名称")
                kb_desc = st.text_area("描述")
                
                col1, col2 = st.columns(2)
                with col1:
                    embedding_source = st.selectbox("嵌入模型来源", list(EMBEDDING_MODELS.keys()))
                with col2:
                    embedding_model = st.selectbox("嵌入模型", list(EMBEDDING_MODELS.get(embedding_source, {}).keys()))
                
                submitted = st.form_submit_button("创建")
                if submitted and kb_name:
                    new_kb = {
                        "id": str(datetime.now().timestamp()),
                        "name": kb_name,
                        "description": kb_desc,
                        "embedding_model": embedding_model,
                        "chunk_size": settings.rag.chunk_size,
                        "chunk_overlap": settings.rag.chunk_overlap,
                        "doc_count": 0,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.session_state.knowledge_bases.append(new_kb)
                    st.session_state.show_create_kb = False
                    st.success("知识库创建成功！")
                    st.rerun()
    
    with tab2:
        st.subheader("上传文档")
        
        # 选择知识库
        if st.session_state.knowledge_bases:
            selected_kb = st.selectbox(
                "选择知识库",
                [kb["name"] for kb in st.session_state.knowledge_bases]
            )
            
            # 文件上传
            uploaded_files = st.file_uploader(
                "选择文件",
                type=["pdf", "txt", "md", "docx", "csv", "html"],
                accept_multiple_files=True
            )
            
            if uploaded_files:
                st.write(f"已选择 {len(uploaded_files)} 个文件")
                
                if st.button("开始处理"):
                    progress_bar = st.progress(0)
                    
                    for i, file in enumerate(uploaded_files):
                        # 模拟处理
                        progress_bar.progress((i + 1) / len(uploaded_files))
                        
                        # 实际应用中应该调用RAG服务处理文档
                        st.toast(f"处理完成: {file.name}")
                    
                    st.success("所有文档处理完成！")
        else:
            st.warning("请先创建知识库")
    
    with tab3:
        st.subheader("检索测试")
        
        if st.session_state.knowledge_bases:
            selected_kb = st.selectbox(
                "选择知识库",
                [kb["name"] for kb in st.session_state.knowledge_bases]
            )
            
            query = st.text_input("输入查询")
            
            if st.button("搜索") and query:
                with st.spinner("搜索中..."):
                    # 模拟搜索结果
                    st.info("检索功能需要后端服务支持")
                    
                    st.markdown("""
                    ### 检索结果示例
                    
                    **文档1: 用户手册.pdf**
                    
                    相关内容：
                    > 这是一段相关的文档内容...
                    
                    相关度: 0.95
                    """)
        else:
            st.warning("请先创建知识库")


if __name__ == "__main__":
    render_knowledge_page()
