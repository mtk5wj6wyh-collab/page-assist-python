"""
Page Assist - Python Edition
主入口文件

使用方法:
    1. Streamlit前端: streamlit run main.py
    2. API服务器: python main.py --api
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def run_streamlit():
    """运行Streamlit前端"""
    import subprocess
    subprocess.run([
        "streamlit", "run",
        str(Path(__file__).parent / "app.py"),
        "--server.port", "8501",
        "--server.address", "localhost"
    ])


def run_api():
    """运行FastAPI后端"""
    from api import run_server
    run_server()


def init_database():
    """初始化数据库"""
    import asyncio
    from database import init_db
    
    async def _init():
        await init_db()
        print("数据库初始化完成!")
    
    asyncio.run(_init())


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="Page Assist - Python Edition")
    parser.add_argument(
        "--mode",
        choices=["streamlit", "api", "init"],
        default="streamlit",
        help="运行模式"
    )
    
    args = parser.parse_args()
    
    if args.mode == "streamlit":
        print("启动 Streamlit 前端...")
        run_streamlit()
    elif args.mode == "api":
        print("启动 API 服务器...")
        run_api()
    elif args.mode == "init":
        print("初始化数据库...")
        init_database()


if __name__ == "__main__":
    main()
