"""数据库引擎与会话管理（SQLAlchemy 2.x）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATA_DIR, settings

# 确保数据库目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

# check_same_thread=False 允许 FastAPI 多线程访问 SQLite
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db():
    """FastAPI 依赖：每个请求一个会话，请求结束关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()