"""
主页 - 重定向到首页（app.py）
"""
import streamlit as st

st.set_page_config(
    page_title="Page Assist",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.switch_page("app.py")
