"""采购域模型：采购订单、收货单。

状态机：
  draft(草稿) --审核--> approved(已审核) --收货--> partially_received(部分收货) --全部收完--> completed(已完成)
  draft/approved --取消--> cancelled(已取消)
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import IDMixin, TimestampMixin


class PurchaseOrder(IDMixin, TimestampMixin, Base):
    __tablename__ = "po_order"

    order_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="采购单号 PO...")
    supplier_id: Mapped[int] = mapped_column(ForeignKey("md_supplier.id"), comment="供应商")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="收货仓库")
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True,
        comment="状态: draft/approved/partially_received/completed/cancelled",
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="订单总额")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    approved_by: Mapped[str | None] = mapped_column(String(50), comment="审核人")
    approved_at: Mapped[str | None] = mapped_column(String(30), comment="审核时间")
    created_by: Mapped[str] = mapped_column(String(50), comment="创建人")
    cancel_reason: Mapped[str | None] = mapped_column(Text, comment="取消原因")

    supplier: Mapped["Supplier"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class PurchaseOrderItem(IDMixin, Base):
    __tablename__ = "po_order_item"

    order_id: Mapped[int] = mapped_column(ForeignKey("po_order.id"), comment="采购单ID")
    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), comment="商品")
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="采购数量")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="采购单价")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="金额=数量*单价")
    received_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="累计已收货数量")

    order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class StockIn(IDMixin, TimestampMixin, Base):
    """收货入库单：审核后的采购订单收货时生成，立即生效并增加库存。"""

    __tablename__ = "po_stock_in"

    stock_in_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="入库单号 SI...")
    po_id: Mapped[int] = mapped_column(ForeignKey("po_order.id"), comment="采购单ID")
    po_no: Mapped[str] = mapped_column(String(30), comment="采购单号")
    supplier_id: Mapped[int] = mapped_column(ForeignKey("md_supplier.id"), comment="供应商")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="入库仓库")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="本次入库金额")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="操作人")

    supplier: Mapped["Supplier"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()
    items: Mapped[list["StockInItem"]] = relationship(cascade="all, delete-orphan")


class StockInItem(IDMixin, Base):
    __tablename__ = "po_stock_in_item"

    stock_in_id: Mapped[int] = mapped_column(ForeignKey("po_stock_in.id"), comment="入库单ID")
    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), comment="商品")
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="入库数量")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="入库单价")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="金额")

    product: Mapped["Product"] = relationship()