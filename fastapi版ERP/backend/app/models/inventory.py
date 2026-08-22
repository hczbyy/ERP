"""库存域模型：库存、流水、盘点、调拨。

核心不变量：任何库存数量变动都必须伴随一条 StockLog（含变动前后快照），
保证可追溯、可对账。
"""
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import IDMixin, TimestampMixin


class Stock(IDMixin, Base):
    __tablename__ = "inv_stock"
    __table_args__ = (UniqueConstraint("product_id", "warehouse_id", name="uq_stock_pw"),)

    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), comment="商品")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="仓库")
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, comment="当前库存数量")

    product: Mapped["Product"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()


class StockLog(IDMixin, Base):
    """库存流水：每次变动一条记录，change_qty 正数入库、负数出库。"""

    __tablename__ = "inv_stock_log"

    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), index=True, comment="商品")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="仓库")
    change_qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), comment="变动数量(正入负出)")
    before_qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), comment="变动前库存")
    after_qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), comment="变动后库存")
    log_type: Mapped[str] = mapped_column(String(20), index=True, comment="类型: purchase_in/sale_out/transfer_in/transfer_out/check_in/check_out/initial")
    ref_no: Mapped[str | None] = mapped_column(String(30), comment="关联单据号")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="操作人")
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), comment="发生时间")

    product: Mapped["Product"] = relationship()


class StockCheck(IDMixin, TimestampMixin, Base):
    """盘点单：draft(草稿) --提交--> done(已完成)。提交后按差异调整库存。"""

    __tablename__ = "inv_stock_check"

    check_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="盘点单号 PC...")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="盘点仓库")
    status: Mapped[str] = mapped_column(String(10), default="draft", comment="状态: draft/done")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="创建人")
    done_by: Mapped[str | None] = mapped_column(String(50), comment="提交人")
    done_at: Mapped[str | None] = mapped_column(String(30), comment="提交时间")

    warehouse: Mapped["Warehouse"] = relationship()
    items: Mapped[list["StockCheckItem"]] = relationship(
        back_populates="check", cascade="all, delete-orphan"
    )


class StockCheckItem(IDMixin, Base):
    __tablename__ = "inv_stock_check_item"

    check_id: Mapped[int] = mapped_column(ForeignKey("inv_stock_check.id"), comment="盘点单ID")
    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), comment="商品")
    book_qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), comment="账面数量")
    actual_qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, comment="实盘数量")
    diff_qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, comment="差异=实盘-账面")

    check: Mapped["StockCheck"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class StockTransfer(IDMixin, TimestampMixin, Base):
    """库存调拨：创建即生效，事务内源仓库减、目标仓库加。"""

    __tablename__ = "inv_stock_transfer"

    transfer_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="调拨单号 TR...")
    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="调出仓库")
    to_warehouse_id: Mapped[int] = mapped_column(ForeignKey("md_warehouse.id"), comment="调入仓库")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="操作人")

    from_warehouse: Mapped["Warehouse"] = relationship(foreign_keys=[from_warehouse_id])
    to_warehouse: Mapped["Warehouse"] = relationship(foreign_keys=[to_warehouse_id])
    items: Mapped[list["StockTransferItem"]] = relationship(
        cascade="all, delete-orphan"
    )


class StockTransferItem(IDMixin, Base):
    __tablename__ = "inv_stock_transfer_item"

    transfer_id: Mapped[int] = mapped_column(ForeignKey("inv_stock_transfer.id"), comment="调拨单ID")
    product_id: Mapped[int] = mapped_column(ForeignKey("md_product.id"), comment="商品")
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 2), comment="调拨数量")

    product: Mapped["Product"] = relationship()