# ═══════════════════════════════════════════════════════════════════
# Gunicorn 配置文件
# 技术栈: Flask + Gunicorn(gevent) + SQLAlchemy + MySQL
# 启动:   gunicorn -c gunicorn.conf.py main:app
# ═══════════════════════════════════════════════════════════════════

import os

# ── 方案选择 ──────────────────────────────────────────────
#   默认方案A（preload_app=False）：根源避免 fork 复制 MySQL 连接
#   PRELOAD=1 切方案B：master 预加载 + post_fork 清理
_USE_PRELOAD = os.getenv("PRELOAD", "0") == "1"

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
workers = int(os.getenv("GUNICORN_WORKERS", "4"))
worker_class = "gevent"
worker_connections = 1000

timeout = 120
graceful_timeout = 30
keepalive = 65
max_requests = 20000
max_requests_jitter = 4000

loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"

preload_app = _USE_PRELOAD


def post_fork(server, worker):
    """方案B：销毁 fork 继承的脏连接池（方案A 不执行）"""
    if not _USE_PRELOAD:
        return
    from app.extensions import db
    from app import create_app
    import gc
    from flask import Flask
    disposed = 0
    try:
        create_app()
        for app_obj in list(db.apps):
            with app_obj.app_context():
                db.engine.dispose()
                disposed += 1
    except Exception:
        pass
    if disposed == 0:
        for obj in gc.get_objects():
            if isinstance(obj, Flask):
                with obj.app_context():
                    db.engine.dispose()
                    disposed += 1
    server.log.info(f"Worker {worker.pid} [方案B]: 清理 {disposed} 个引擎")


def worker_exit(server, worker):
    """Worker 退出时清理连接（进程退出时 OS 自动关闭 fd，此为双重保障）"""
    from app.extensions import db
    try:
        import sys
        # 用 sys.modules 取已加载的 app 实例，避免 create_app 创建新引擎
        for mod_name, mod in list(sys.modules.items()):
            if hasattr(mod, 'app') and hasattr(getattr(mod, 'app'), 'extensions'):
                app = getattr(mod, 'app')
                try:
                    with app.app_context():
                        db.engine.dispose()
                    server.log.info(f"Worker {worker.pid}: 连接池已关闭")
                except Exception:
                    pass
                break
    except Exception:
        pass