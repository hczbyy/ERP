"""应用配置：集中管理数据库、JWT、种子数据开关。"""
from pathlib import Path

# 项目根目录（backend/）
BASE_DIR = Path(__file__).resolve().parent.parent
# 数据库文件位置（SQLite，Python 自带，无需额外安装）
DATA_DIR = BASE_DIR / "data"


class Settings:
    APP_NAME = "OpenERP 企业资源管理系统"
    VERSION = "1.0.0"

    # ---- 数据库 ----
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'erp.db'}"

    # ---- JWT ----
    JWT_SECRET = "openerp-dev-secret-change-me-in-production"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 480  # 8 小时

    # ---- 安全 ----
    PASSWORD_SALT_ITERATIONS = 100_000

    # ---- 初始化 ----
    SEED_DEMO_DATA = True  # 首次启动自动写入演示数据


settings = Settings()