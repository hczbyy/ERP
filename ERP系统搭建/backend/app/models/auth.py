"""认证与授权模型：用户、角色、权限（RBAC）。"""
from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import IDMixin, TimestampMixin

# 用户-角色 多对多
user_roles = Table(
    "sys_user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
)

# 角色-权限 多对多
role_permissions = Table(
    "sys_role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("sys_permission.id", ondelete="CASCADE"), primary_key=True),
)


class User(IDMixin, TimestampMixin, Base):
    __tablename__ = "sys_user"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="登录名")
    password_hash: Mapped[str] = mapped_column(String(256), comment="密码哈希")
    display_name: Mapped[str] = mapped_column(String(50), comment="姓名")
    email: Mapped[str | None] = mapped_column(String(100), comment="邮箱")
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="超级管理员（跳过权限校验）")

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")


class Role(IDMixin, TimestampMixin, Base):
    __tablename__ = "sys_role"

    code: Mapped[str] = mapped_column(String(50), unique=True, comment="角色编码")
    name: Mapped[str] = mapped_column(String(50), comment="角色名称")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, comment="内置角色不可删除")

    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles"
    )


class Permission(IDMixin, Base):
    __tablename__ = "sys_permission"

    code: Mapped[str] = mapped_column(String(100), unique=True, comment="权限点编码，如 master:product:manage")
    name: Mapped[str] = mapped_column(String(50), comment="权限点名称")
    module: Mapped[str] = mapped_column(String(50), index=True, comment="所属模块")

    roles: Mapped[list["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")