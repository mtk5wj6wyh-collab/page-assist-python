"""
Page Assist — 桌面客户端入口
启动 Streamlit 服务器并嵌入原生窗口
"""
import sys
import os
import threading
import subprocess
import time
import webbrowser
from pathlib import Path

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

STREAMLIT_PORT = 8501
STREAMLIT_URL = f"http://localhost:{STREAMLIT_PORT}"


def start_streamlit():
    """在后台线程启动 Streamlit 服务器"""
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(ROOT_DIR / "app.py"),
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "localhost",
        "--server.headless", "true",         # 不自动打开浏览器
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false",
    ]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATED_NO_WINDOW') else 0
    )


def wait_for_server(url, timeout=30):
    """等待 Streamlit 服务器就绪"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"{url}/_stcore/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    """桌面客户端入口"""
    print("🚀 正在启动 Page Assist 桌面客户端...")

    # 启动 Streamlit 服务器
    process = start_streamlit()

    # 等待服务器就绪
    if not wait_for_server(STREAMLIT_URL):
        print("❌ Streamlit 启动超时")
        process.kill()
        sys.exit(1)

    print(f"✅ Streamlit 已就绪 → {STREAMLIT_URL}")
    print("📦 正在打开桌面窗口...")

    try:
        import webview

        # 创建原生窗口
        window = webview.create_window(
            title="Page Assist",
            url=STREAMLIT_URL,
            width=1280,
            height=800,
            min_size=(900, 600),
            resizable=True,
            text_select=True,
            easy_drag=False,
        )
        webview.start(
            private_mode=False,
            storage_path=str(ROOT_DIR / ".webview_cache"),
        )
    except ImportError:
        # pywebview 未安装，回退到浏览器
        print("⚠️ pywebview 未安装，将在默认浏览器中打开")
        webbrowser.open(STREAMLIT_URL)
        process.wait()
    except Exception as e:
        print(f"⚠️ 桌面窗口异常: {e}")
        print(f"   可在浏览器中手动访问: {STREAMLIT_URL}")
        webbrowser.open(STREAMLIT_URL)
        process.wait()
    finally:
        print("🛑 正在关闭服务...")
        process.terminate()
        process.wait(timeout=5)
        print("👋 已退出")


if __name__ == "__main__":
    main()
