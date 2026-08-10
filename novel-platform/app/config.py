"""应用配置

改动说明：
  - pool_use_lifo=True：gevent 协程模型下优先复用最近连接，减少连接创建
  - pool_pre_ping=True：每次取连接前探测，避免返回已断开的连接
  - pool_recycle=3600：连接最大存活 1 小时，配合 MySQL wait_timeout
  - pool_size=40：单个 worker 的常驻连接数
  - max_overflow=20：瞬时尖峰允许的额外连接

连接数计算公式：
  总连接数 ≈ workers × (pool_size + avg_overflow)
  例：2 workers × (40 + 5~10) ≈ 90~100  ← 用户观察到的 90+ 是正常的
"""

import os


class Config:
    # ── MySQL 连接 ──────────────────────────────────────────────
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
    DB_NAME = os.getenv("DB_NAME", "app")
    DB_CHARSET = "utf8mb4"

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset={DB_CHARSET}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── 连接池（gevent worker 优化） ──────────────────────────
    SQLALCHEMY_ENGINE_OPTIONS = {
        # ★ 企业级：单 worker 常驻 28 + 溢出 7 = 硬上限 35
        #   4 workers × 35 = 140，距 MySQL max_connections(151) 留 11 余量
        "pool_size": 28,          # 写操作占连接时间更长，适当放大
        "max_overflow": 7,        # 突发流量再给 7 条缓冲

        # 连接健康 -------------------------------------------------
        "pool_pre_ping": True,     # 取连接前 SELECT 1 探测，防拿到坏连接
        "pool_recycle": 180,       # 3 分钟回收，避免 MySQL 侧 wait_timeout 断连

        # gevent 优化 ---------------------------------------------
        "pool_use_lifo": True,     # gevent 下优先复用最近归还的连接（热连接缓存）

        # 超时 ----------------------------------------------------
        "pool_timeout": 30,        # 写操作排队等连接最大 30 秒，减少超时报错
        "echo_pool": False,
    }

    # ── 缓存 TTL（秒） ──────────────────────────────────────
    CACHE_NOVEL_LIST_TTL = 5
    CACHE_NOVEL_DETAIL_TTL = 10
    CACHE_CATEGORIES_TTL = 30
    CACHE_STATS_TTL = 5
    CACHE_MAXSIZE = 500

    # ── JWT ─────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "novel-platform-jmeter-secret-key-2026")
    JWT_SALT = "auth"
    JWT_EXPIRE_HOURS = 72

    # ── Flask ───────────────────────────────────────────────
    JSON_AS_ASCII = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024


class TestConfig(Config):
    TESTING = True