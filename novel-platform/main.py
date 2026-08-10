# ★★★ gevent 猴子补丁：文件【绝对第一行】，所有模块导入之前执行 ★★★
#   修补 socket/ssl/threading/select/time/os/signal/queue 等
#   任何业务模块在补丁前被导入都会导致补丁不生效
import gevent.monkey  # noqa: E402
gevent.monkey.patch_all()  # noqa: E402

# ★ PyMySQL 注册为 MySQLdb 驱动，确保 SQLAlchemy 在 gevent 下正确处理连接
import pymysql  # noqa: E402
pymysql.install_as_MySQLdb()  # noqa: E402

"""
小说平台 — 统一入口

设计目标：
  Gunicorn(gevent) 正式压测 + Flask/Waitress 本地调试 双模式

连接泄漏问题 — 产生原理：
  Gunicorn preload_app=True 时，master 进程创建 engine 并初始化连接池。
  fork() 后子进程继承 master 内存快照，包括已建立的 MySQL fd。
  这些 fd 连接不受 SQLAlchemy 连接池管理（pool 只知道 fork 前的状态），
  MySQL 端认为连接仍有效，Threads_connected 持续上涨。
  当 pool 内已标记为 "归还" 的连接在 fork 后实际已不可用时，
  新请求创建新连接但旧连接不被释放 → 连接泄漏 → 服务雪崩。

  解决方案见 gunicorn.conf.py 方案A/方案B。

运行模式：
  ① 正式压测  → gunicorn -c gunicorn.conf.py main:app
     走 gevent 协程模型，多 worker 并发
  ② 本地调试  → python main.py [options]
     使用 Flask 内置服务器（多线程）或 Waitress（线程池）
"""

# ═══════════════════════════════════════════════════════════════════
# 业务模块导入（补丁之后，安全）
# ═══════════════════════════════════════════════════════════════════

import sys
import os

# 将项目根目录加入 sys.path，确保 import app 正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app  # noqa: E402

# ── 全局 app 实例（gunicorn 加载 main:app 时使用此变量） ──
#   gunicorn 从 main.py 读取 `app` 属性作为 WSGI 应用
#   不会触发 `if __name__ == "__main__"` 分支
app = create_app()

# ═══════════════════════════════════════════════════════════════════
# 本地调试入口（仅 python main.py 时进入）
# ═══════════════════════════════════════════════════════════════════
#
#   重要：
#     argparse 参数逻辑放在 __main__ 块内，避免 gunicorn 加载顶层模块时
#     因 import argparse 产生副作用。gunicorn 加载 main:app 时 __name__
#     为 "main"，不是 "__main__"，不会进入此分支。
#
#   当前支持三种本地运行方式：
#     1. Flask 内置服务器（默认）  → 适合快速调试
#     2. Waitress 线程池模式      → 更接近生产的多线程行为
#     3. 绝不在此处使用 gevent     → gevent 仅由外部 gunicorn -k gevent 激活
#
if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="小说平台 — 本地调试")
    parser.add_argument("-p", "--port", type=int, default=5000, help="监听端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument(
        "--threads", type=int, default=20,
        help="线程数（Waitress 模式）",
    )
    parser.add_argument(
        "--waitress", action="store_true",
        help="使用 Waitress 生产服务器（线程池模式）",
    )
    parser.add_argument("--debug", action="store_true", help="Flask 调试模式")
    args = parser.parse_args()

    # ── 打印启动信息 ──────────────────────────────────────
    mode_label = "Waitress（线程池）" if args.waitress else "Flask 内置（多线程）"
    print(
        f"  [启动] 小说平台\n"
        f"  模式: {mode_label}\n"
        f"  地址: http://{args.host}:{args.port}\n"
    )

    if args.waitress:
        # ── Waitress 生产服务器（纯线程） ────────────────
        try:
            from waitress import serve
        except ImportError:
            print("[错误] 请安装 waitress: pip install waitress")
            sys.exit(1)

        serve(
            app,
            host=args.host,
            port=args.port,
            threads=args.threads,
            connection_limit=500,
            channel_request_lookahead=0,
            url_scheme="http",
        )
    else:
        # ── Flask 内置开发服务器（多线程） ────────────────
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True,
            processes=1,
        )