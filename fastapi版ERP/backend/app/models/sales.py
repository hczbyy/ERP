"""销售域模型：销售订单、发货单。

状态机：
  draft(草稿) --审核--> approved(已审核) --发货--> partially_shipped(部分发货) --全部发完--> completed(已完成)
  draft/approved --取消--> cancelled(已取消)
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import IDMixin, TimestampMixin


class SalesOrder(IDMixin, TimestampMixin, Base):
    __tablename__ = "so_order"

    order_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="销售单号 SO...")
    customer_id: Mapped[int] = mapped_column(ForeignKey("md_customer.id"), comment="客户")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="发货仓库")
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True,
        comment="状态: draft/approved/partially_shipped/completed/cancelled",
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="订单总额")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    approved_by: Mapped[str | None] = mapped_column(String(50), comment="审核人")
    approved_at: Mapped[str | None] = mapped_column(String(30), comment="审核时间")
    created_by: Mapped[str] = mapped_column(String(50), comment="创建人")
    cancel_reason: Mapped[str | None] = mapped_column(Text, comment="取消原因")

    customer: Mapped["Customer"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()
    items: Mapped[list["SalesOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class SalesOrderItem(IDMixin, Base):
    __tablename__ = "so_order_item"

    order_id: Mapped[int] = mapped_column(ForeignKey("so_order.id"), comment="销售单ID")
    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), comment="商品")
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="销售数量")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="销售单价")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="金额=数量*单价")
    shipped_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="累计已发货数量")

    order: Mapped["SalesOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class StockOut(IDMixin, TimestampMixin, Base):
    """发货出库单：审核后的销售订单发货时生成，立即生效并扣减库存。"""

    __tablename__ = "so_stock_out"

    stock_out_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="出库单号 SOUT...")
    so_id: Mapped[int] = mapped_column(ForeignKey("so_order.id"), comment="销售单ID")
    so_no: Mapped[str] = mapped_column(String(30), comment="销售单号")
    customer_id: Mapped[int] = mapped_column(ForeignKey("md_customer.id"), comment="客户")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="发货仓库")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="本次发货金额")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="操作人")

    customer: Mapped["Customer"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()
    items: Mapped[list["StockOutItem"]] = relationship(cascade="all, delete-orphan")


class StockOutItem(IDMixin, Base):
    __tablename__ = "so_stock_out_item"

    stock_out_id: Mapped[int] = mapped_column(ForeignKey("so_stock_out.id"), comment="出库单ID")
    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), comment="商品")
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="出库数量")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="出库单价")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="金额")

    product: Mapped["Product"] = relationship()