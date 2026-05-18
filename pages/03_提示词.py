"""
提示词管理页面
"""
import streamlit as st
from datetime import datetime
from config import settings


def render_prompt_page():
    """渲染提示词管理页面"""
    st.set_page_config(
        page_title=f"提示词 - {settings.app_name}",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 提示词管理")
    
    # 初始化状态
    if "prompts" not in st.session_state:
        st.session_state.prompts = [
            {
                "id": "1",
                "name": "翻译助手",
                "content": "你是一个专业的翻译助手。请将以下内容翻译成{{language}}：\n\n{{content}}",
                "description": "翻译选定或输入的内容",
                "category": "assistant",
                "is_copilot": True,
                "trigger": "翻译",
                "tags": ["翻译", "助手"],
                "use_count": 10
            },
            {
                "id": "2",
                "name": "内容总结",
                "content": "请总结以下内容的主要要点：\n\n{{content}}",
                "description": "总结文本内容",
                "category": "assistant",
                "is_copilot": True,
                "trigger": "总结",
                "tags": ["总结", "助手"],
                "use_count": 5
            },
            {
                "id": "3",
                "name": "代码审查",
                "content": "请审查以下代码，指出潜在问题和改进建议：\n\n```\n{{code}}\n```",
                "description": "代码审查助手",
                "category": "programming",
                "is_copilot": False,
                "tags": ["编程", "代码"],
                "use_count": 3
            }
        ]
    
    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["提示词列表", "创建提示词", "Copilot设置"])
    
    with tab1:
        st.subheader("我的提示词")
        
        # 筛选选项
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_category = st.selectbox(
                "分类",
                ["全部", "自定义", "编程", "写作", "翻译", "分析"]
            )
        with col2:
            search_query = st.text_input("搜索提示词", placeholder="输入关键词搜索...")
        
        # 显示提示词列表
        filtered_prompts = st.session_state.prompts
        
        if filter_category != "全部":
            filtered_prompts = [p for p in filtered_prompts if p.get("category") == filter_category.lower()]
        
        if search_query:
            filtered_prompts = [
                p for p in filtered_prompts 
                if search_query.lower() in p["name"].lower() or search_query.lower() in p.get("content", "").lower()
            ]
        
        for prompt in filtered_prompts:
            with st.expander(f"{'🤖' if prompt.get('is_copilot') else '📝'} {prompt['name']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.code(prompt["content"], language="markdown")
                    if prompt.get("description"):
                        st.caption(f"描述: {prompt['description']}")
                    if prompt.get("tags"):
                        st.write("标签:", ", ".join(prompt.get("tags", [])))
                    st.caption(f"使用次数: {prompt.get('use_count', 0)}")
                with col2:
                    if st.button("编辑", key=f"edit_{prompt['id']}"):
                        st.session_state.edit_prompt_id = prompt["id"]
                        st.rerun()
                    if st.button("删除", key=f"del_{prompt['id']}"):
                        st.session_state.prompts = [p for p in st.session_state.prompts if p["id"] != prompt["id"]]
                        st.rerun()
                    if st.button("复制", key=f"copy_{prompt['id']}"):
                        st.code(prompt["content"])
                        st.toast("已复制到剪贴板")
    
    with tab2:
        st.subheader("创建新提示词")
        
        with st.form("create_prompt_form"):
            name = st.text_input("提示词名称", placeholder="例如：翻译助手")
            description = st.text_area("描述", placeholder="提示词的简短描述")
            content = st.text_area(
                "提示词内容",
                height=200,
                placeholder="使用 {{variable}} 表示变量..."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox(
                    "分类",
                    ["自定义", "编程", "写作", "翻译", "分析", "创意"]
                )
                tags = st.text_input("标签", placeholder="用逗号分隔")
            with col2:
                is_copilot = st.checkbox("作为Copilot使用")
                if is_copilot:
                    trigger = st.text_input("触发词", placeholder="例如：翻译")
            
            submitted = st.form_submit_button("创建提示词")
            
            if submitted and name and content:
                new_prompt = {
                    "id": str(datetime.now().timestamp()),
                    "name": name,
                    "content": content,
                    "description": description,
                    "category": category.lower(),
                    "is_copilot": is_copilot,
                    "trigger": trigger if is_copilot else None,
                    "tags": [t.strip() for t in tags.split(",")] if tags else [],
                    "use_count": 0
                }
                st.session_state.prompts.append(new_prompt)
                st.success("提示词创建成功！")
                st.rerun()
    
    with tab3:
        st.subheader("Copilot设置")
        
        copilot_prompts = [p for p in st.session_state.prompts if p.get("is_copilot")]
        
        if copilot_prompts:
            st.write("已启用的Copilot功能：")
            
            for prompt in copilot_prompts:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.checkbox("启用", key=f"copilot_enable_{prompt['id']}", value=True)
                with col2:
                    st.write(f"**{prompt['name']}**")
                    st.caption(f"触发词: {prompt.get('trigger', '无')}")
                with col3:
                    st.write(f"使用 {prompt.get('use_count', 0)} 次")
        else:
            st.info("暂无启用的Copilot功能，请在提示词列表中创建并启用")


if __name__ == "__main__":
    render_prompt_page()
