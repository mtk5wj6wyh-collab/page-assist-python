"""
Page Assist — PyInstaller 打包脚本
将 Python 版打包为独立的 Windows 桌面安装程序
"""
import sys
import os
from pathlib import Path
import PyInstaller.__main__

ROOT = Path(__file__).parent.resolve()
OUTPUT = ROOT / "dist"

# 应用名称
APP_NAME = "Page Assist"

# 需要打包的额外数据（pages 目录等）
datas = [
    (str(ROOT / "pages"), "pages"),
    (str(ROOT / ".env.example"), "."),
]

datas_args = []
for src, dst in datas:
    datas_args.append(f"--add-data={src}{os.pathsep}{dst}")

# 隐式导入（PyInstaller 可能遗漏的模块）
hidden_imports = [
    "--hidden-import=streamlit",
    "--hidden-import=streamlit.web.cli",
    "--hidden-import=streamlit.runtime.scriptrunner",
    "--hidden-import=config",
    "--hidden-import=database",
    "--hidden-import=services.ai_provider",
    "--hidden-import=services.chat_manager",
    "--hidden-import=services.search",
    "--hidden-import=services.rag",
    "--hidden-import=services.tts",
    "--hidden-import=services.mcp",
    "--hidden-import=services.prompt_manager",
    "--hidden-import=models.chat",
    "--hidden-import=models.knowledge",
    "--hidden-import=models.prompt",
    "--hidden-import=models.settings",
    "--hidden-import=utils.file_handler",
    "--hidden-import=utils.markdown",
    "--hidden-import=utils.config_store",
    "--hidden-import=webview",
    "--hidden-import=pydantic",
    "--hidden-import=pydantic_settings",
    "--hidden-import=sqlalchemy",
    "--hidden-import=aiosqlite",
    "--hidden-import=chromadb",
    "--hidden-import=httpx",
    "--hidden-import=aiohttp",
    "--hidden-import=dotenv",
    "--hidden-import=bs4",
    "--hidden-import=docx",
    "--hidden-import=pypdf",
    "--hidden-import=edge_tts",
    "--hidden-import=langchain",
]

PyInstaller.__main__.run([
    "--name", APP_NAME,
    "--onefile",                    # 单文件 .exe
    "--windowed",                   # 无控制台窗口（GUI 模式）
    "--noconfirm",
    "--clean",
    "--log-level", "WARN",
    "--distpath", str(OUTPUT),
    "--workpath", str(ROOT / "build"),
    "--specpath", str(ROOT),
    *datas_args,
    *hidden_imports,
    str(ROOT / "desktop.py"),       # 入口
])

print(f"\n✅ 打包完成！")
print(f"📦 输出目录: {OUTPUT}")
print(f"🚀 运行: {OUTPUT / APP_NAME}.exe")
