# -*- coding: utf-8 -*-
"""平台启动入口：自动加载 D:\\ai测试平台依赖包 中的依赖并启动服务。"""
import os
import socket
import sys
import threading
import time
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPS_DIR = os.path.join(os.path.dirname(BASE_DIR), "ai测试平台依赖包")
if os.path.isdir(DEPS_DIR):
    sys.path.insert(0, DEPS_DIR)
sys.path.insert(0, BASE_DIR)

import uvicorn  # noqa: E402


def find_free_port(start: int = 8000, end: int = 8015) -> int:
    for port in range(start, end + 1):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


_env_port = os.environ.get("AI_TEST_PORT", "")
PORT = int(_env_port) if _env_port else find_free_port()


def open_browser():
    time.sleep(1.8)
    webbrowser.open(f"http://127.0.0.1:{PORT}")


if __name__ == "__main__":
    print("=" * 56)
    print("  AI 接口测试平台 启动中...")
    print(f"  访问地址: http://127.0.0.1:{PORT}")
    print("  关闭本窗口即可停止服务")
    print("=" * 56)
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=PORT, reload=False)
