"""
文件处理工具
"""
import os
import uuid
from pathlib import Path
from typing import List, Optional, Tuple
import base64


ALLOWED_EXTENSIONS = {
    "pdf": ["pdf"],
    "document": ["txt", "md", "docx", "doc"],
    "image": ["png", "jpg", "jpeg", "gif", "webp"],
    "data": ["csv", "json", "xml"],
    "web": ["html", "htm"],
}


def get_file_type(filename: str) -> str:
    """获取文件类型"""
    ext = Path(filename).suffix.lower().lstrip(".")
    
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    
    return "unknown"


def is_allowed_file(filename: str) -> bool:
    """检查文件是否允许上传"""
    ext = Path(filename).suffix.lower().lstrip(".")
    
    for extensions in ALLOWED_EXTENSIONS.values():
        if ext in extensions:
            return True
    
    return False


def get_mime_type(filename: str) -> str:
    """获取MIME类型"""
    ext = Path(filename).suffix.lower().lstrip(".")
    
    mime_types = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
        "html": "text/html",
        "htm": "text/html",
    }
    
    return mime_types.get(ext, "application/octet-stream")


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def save_uploaded_file(uploaded_file, upload_dir: str) -> Tuple[str, str]:
    """保存上传的文件
    
    Returns:
        Tuple[str, str]: (file_path, file_id)
    """
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_ext = Path(uploaded_file.name).suffix
    filename = f"{file_id}{file_ext}"
    file_path = upload_path / filename
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path), file_id


def read_file_content(file_path: str) -> str:
    """读取文件内容"""
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    encoding = "utf-8"
    
    # 检测编码
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except UnicodeDecodeError:
        encoding = "gbk"
    
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def delete_file(file_path: str) -> bool:
    """删除文件"""
    path = Path(file_path)
    
    if path.exists():
        path.unlink()
        return True
    
    return False


def create_temp_copy(src_path: str, temp_dir: str) -> str:
    """创建临时文件副本"""
    import shutil
    
    src = Path(src_path)
    temp_path = Path(temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)
    
    dest = temp_path / src.name
    shutil.copy2(src, dest)
    
    return str(dest)
