"""组织架构模型：部门、员工。"""
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import IDMixin, TimestampMixin


class Department(IDMixin, TimestampMixin, Base):
    __tablename__ = "org_department"

    code: Mapped[str] = mapped_column(String(20), unique=True, comment="部门编码")
    name: Mapped[str] = mapped_column(String(50), comment="部门名称")
    leader: Mapped[str | None] = mapped_column(String(50), comment="负责人")
    phone: Mapped[str | None] = mapped_column(String(20), comment="电话")
    remark: Mapped[str | None] = mapped_column(String(200), comment="备注")


class Employee(IDMixin, TimestampMixin, Base):
    __tablename__ = "org_employee"

    emp_no: Mapped[str] = mapped_column(String(20), unique=True, comment="工号")
    name: Mapped[str] = mapped_column(String(50), comment="姓名")
    gender: Mapped[str | None] = mapped_column(String(10), comment="性别")
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")
    email: Mapped[str | None] = mapped_column(String(100), comment="邮箱")
    hire_date: Mapped[date | None] = mapped_column(Date, comment="入职日期")
    position: Mapped[str | None] = mapped_column(String(50), comment="职位")
    status: Mapped[str] = mapped_column(String(10), default="active", comment="状态: active/left")
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_department.id"), comment="所属部门"
    )

    department: Mapped["Department | None"] = relationship()