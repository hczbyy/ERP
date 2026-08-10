"""启动脚本：python run.py

不依赖工作目录 —— 无论在 PyCharm 中直接运行，还是在命令行任意路径执行，
都会自动定位 backend 目录并加入模块搜索路径。
"""
import os
import sys
from pathlib import Path

# Windows 控制台默认 GBK，输出中文可能崩溃，强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 将 backend 目录加入 sys.path（无论当前工作目录在哪）
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)  # 保证 SQLite 数据库文件落在 backend/data/ 下

import uvicorn  # noqa: E402

if __name__ == "__main__":
    # reload=False：避免 PyCharm 调试器与 uvicorn 子进程冲突
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)