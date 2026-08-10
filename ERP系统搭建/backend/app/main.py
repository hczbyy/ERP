"""应用入口：创建 FastAPI 实例、注册路由与异常处理、托管前端静态文件。

支持两种运行方式：
  1. PyCharm 直接运行本文件（或 python app/main.py）
  2. 模块方式：uvicorn app.main:app
"""
import sys
from pathlib import Path

# 兼容：以脚本方式直接运行时（PyCharm Run / python app/main.py），
# 手动补齐包上下文，使下方相对导入可用
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "app"

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .api import auth, dashboard, finance, inventory, master, purchase, sales, system
from .config import settings
from .database import Base, SessionLocal, engine
from .seed import seed_if_empty
from .utils import BusinessError, fail

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


class NoCacheStaticFiles(StaticFiles):
    """开发期静态资源禁用缓存，避免前端改动后浏览器仍加载旧 JS/CSS。"""

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="OpenERP 企业资源管理系统：采购、销售、库存、财务一体化",
    )

    # ---- 注册业务路由 ----
    for r in (auth.router, system.router, master.router, purchase.router,
              sales.router, inventory.router, finance.router, dashboard.router):
        app.include_router(r)

    # ---- 统一响应包装：业务异常 ----
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        return JSONResponse(status_code=exc.code, content=fail(exc.message))

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        # 兜底：未捕获异常返回 500（避免堆栈泄露给前端）
        return JSONResponse(status_code=500, content=fail(f"服务器内部错误: {exc}"))

    # ---- 健康检查 ----
    @app.get("/api/health")
    def health():
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}

    # ---- 初始化数据库 + 种子数据 ----
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
    seed_if_empty()

    # ---- 托管前端（零构建 SPA，禁用缓存）----
    if FRONTEND_DIR.exists():
        app.mount("/", NoCacheStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    else:
        @app.get("/")
        def root():
            return {"message": "后端运行正常，前端目录不存在", "docs": "/docs"}

    return app


app = create_app()

if __name__ == "__main__":
    import os
    import socket

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))

    # 预检端口占用：给测试人员明确的提示，而不是一长串 errno
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        print(f"[错误] 端口 {port} 已被其他程序占用。\n"
              f"  方案一：关闭占用该端口的程序后重试\n"
              f"  方案二：改用其他端口启动，例如设置环境变量 PORT=8001 后重新运行")
        sys.exit(1)
    finally:
        probe.close()

    uvicorn.run(app, host="127.0.0.1", port=port)