"""通用模型字段与工具：主键、时间戳、统一序列化。"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TimestampMixin:
    """所有业务表共用的创建/更新时间戳。"""

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class IDMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")


def to_dict(obj, exclude: set[str] | None = None) -> dict:
    """ORM 对象转 dict（用于审计日志等通用场景）。"""
    exclude = exclude or set()
    return {
        c.name: getattr(obj, c.name)
        for c in obj.__table__.columns
        if c.name not in exclude and not c.name.startswith("_")
    }