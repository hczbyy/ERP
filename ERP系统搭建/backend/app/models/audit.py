"""审计日志模型：记录关键操作，供追溯审计。"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .base import IDMixin


class AuditLog(IDMixin, Base):
    __tablename__ = "sys_audit_log"

    username: Mapped[str] = mapped_column(String(50), index=True, comment="操作人")
    action: Mapped[str] = mapped_column(String(30), index=True, comment="动作: login/create/update/delete/approve/receive/ship/check/transfer/pay/cancel")
    module: Mapped[str] = mapped_column(String(50), index=True, comment="模块")
    target: Mapped[str | None] = mapped_column(String(100), comment="操作对象(如单号)")
    detail: Mapped[str | None] = mapped_column(Text, comment="详情(JSON字符串)")
    ip: Mapped[str | None] = mapped_column(String(50), comment="来源IP")
    created_at: Mapped[str] = mapped_column(String(30), comment="时间(ISO)")