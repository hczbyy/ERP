"""基础数据模型：商品分类、商品、客户、供应商、仓库。"""
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import IDMixin, TimestampMixin


class ProductCategory(IDMixin, TimestampMixin, Base):
    __tablename__ = "md_category"

    name: Mapped[str] = mapped_column(String(50), unique=True, comment="分类名称")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("md_category.id"), comment="上级分类")
    sort: Mapped[int] = mapped_column(default=0, comment="排序")


class Product(IDMixin, TimestampMixin, Base):
    __tablename__ = "md_product"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="商品编码(SKU)")
    name: Mapped[str] = mapped_column(String(100), index=True, comment="商品名称")
    spec: Mapped[str | None] = mapped_column(String(100), comment="规格型号")
    unit: Mapped[str] = mapped_column(String(20), default="件", comment="计量单位")
    barcode: Mapped[str | None] = mapped_column(String(50), comment="条码")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("md_category.id"), comment="分类")
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="采购价")
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="销售价")
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="安全库存(预警线)")
    status: Mapped[str] = mapped_column(String(10), default="active", comment="状态: active/disabled")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")

    category: Mapped["ProductCategory | None"] = relationship()


class Customer(IDMixin, TimestampMixin, Base):
    __tablename__ = "md_customer"

    code: Mapped[str] = mapped_column(String(20), unique=True, comment="客户编码")
    name: Mapped[str] = mapped_column(String(100), index=True, comment="客户名称")
    contact: Mapped[str | None] = mapped_column(String(50), comment="联系人")
    phone: Mapped[str | None] = mapped_column(String(20), comment="联系电话")
    address: Mapped[str | None] = mapped_column(String(200), comment="地址")
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="信用额度")
    status: Mapped[str] = mapped_column(String(10), default="active", comment="状态: active/disabled")


class Supplier(IDMixin, TimestampMixin, Base):
    __tablename__ = "md_supplier"

    code: Mapped[str] = mapped_column(String(20), unique=True, comment="供应商编码")
    name: Mapped[str] = mapped_column(String(100), index=True, comment="供应商名称")
    contact: Mapped[str | None] = mapped_column(String(50), comment="联系人")
    phone: Mapped[str | None] = mapped_column(String(20), comment="联系电话")
    address: Mapped[str | None] = mapped_column(String(200), comment="地址")
    status: Mapped[str] = mapped_column(String(10), default="active", comment="状态: active/disabled")


class Warehouse(IDMixin, TimestampMixin, Base):
    __tablename__ = "md_warehouse"

    code: Mapped[str] = mapped_column(String(20), unique=True, comment="仓库编码")
    name: Mapped[str] = mapped_column(String(50), comment="仓库名称")
    address: Mapped[str | None] = mapped_column(String(200), comment="地址")
    manager: Mapped[str | None] = mapped_column(String(50), comment="负责人")
    status: Mapped[str] = mapped_column(String(10), default="active", comment="状态: active/disabled")