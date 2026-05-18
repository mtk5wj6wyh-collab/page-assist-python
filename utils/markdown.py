"""
Markdown工具函数
"""
import re


def render_markdown(text: str) -> str:
    """渲染Markdown文本"""
    # 简单的Markdown渲染
    # 实际使用中可以集成markdown或markdown2库
    
    # 代码块
    text = re.sub(
        r'```(\w+)?\n(.*?)\n```',
        r'<pre><code class="\1">\2</code></pre>',
        text,
        flags=re.DOTALL
    )
    
    # 行内代码
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # 标题
    for i in range(6, 0, -1):
        text = re.sub(rf'^({"#" * i}) (.+)$', rf'<h{i}>\2</h{i}>', text, flags=re.MULTILINE)
    
    # 粗体
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # 斜体
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    # 链接
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    
    # 列表
    text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', text)
    
    # 换行
    text = text.replace('\n', '<br>')
    
    return text


def clean_markdown_for_tts(text: str) -> str:
    """清理Markdown文本以适合TTS"""
    # 移除代码块
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # 移除行内代码
    text = re.sub(r'`[^`]+`', '', text)
    
    # 移除链接文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # 移除图片
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
    
    # 移除标题标记
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # 移除列表标记
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)
    
    # 移除加粗和斜体标记
    text = re.sub(r'\*+', '', text)
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 清理多余空格
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_code_blocks(text: str) -> list:
    """提取代码块"""
    pattern = r'```(\w+)?\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL)
    return [
        {"language": lang or "text", "code": code.strip()}
        for lang, code in matches
    ]


def extract_images(text: str) -> list:
    """提取图片"""
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(pattern, text)
    return [
        {"alt": alt, "url": url}
        for alt, url in matches
    ]


def extract_links(text: str) -> list:
    """提取链接"""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, text)
    return [
        {"text": text, "url": url}
        for text, url in matches
    ]
