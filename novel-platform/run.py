"""小说平台 — 启动入口

强制规范：gevent 猴子补丁必须放在所有导入最顶部
"""

# ── ★★★ gevent 猴子补丁：必须放在第一位 ★★★ ──────────
import gevent.monkey
gevent.monkey.patch_all()

# ── 业务导入（补丁之后） ─────────────────────────────────
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="小说平台 - JMeter 练习用")
    parser.add_argument("-p", "--port", type=int, default=5000, help="监听端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--threads", type=int, default=None, help="线程数（Flask 模式）")
    parser.add_argument("--workers", type=int, default=None, help="进程数（Waitress 模式）")
    parser.add_argument("--waitress", action="store_true", help="使用 Waitress 生产服务器")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    args = parser.parse_args()

    workers = args.workers or int(os.getenv("GUNICORN_WORKERS", "2"))
    threads = args.threads or int(os.getenv("GUNICORN_THREADS", "20"))
    pool_size = Config.SQLALCHEMY_ENGINE_OPTIONS["pool_size"]

    mode = "Waitress（多进程+多线程）" if args.waitress else "Flask 内置（多线程）"

    print(f"""
{'=' * 55}
  小说平台 — JMeter 练习环境
{'=' * 55}
  地址:      http://{args.host}:{args.port}
  模式:      {mode}
  进程数:    {workers}
  每进程线程: {threads}
  连接池/进程: {pool_size}
  总并发容量: ~{workers * (pool_size + Config.SQLALCHEMY_ENGINE_OPTIONS.get('max_overflow', 0))} 数据库连接
{'=' * 55}
""")

    if args.waitress:
        try:
            from waitress import serve
        except ImportError:
            print("[ERROR] 请先安装 waitress: pip install waitress")
            sys.exit(1)

        serve(
            app,
            host=args.host,
            port=args.port,
            threads=threads,
            connection_limit=500,
            channel_request_lookahead=0,
            url_scheme="http",
        )
    else:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True,
            processes=1,
        )