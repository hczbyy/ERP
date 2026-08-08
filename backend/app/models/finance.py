"""财务域模型：应收、应付、收款单、付款单。

业务规则：
  - 应收由销售发货单自动生成；应付由采购收货单自动生成（按实际收/发金额）。
  - 一笔应收可多次收款核销，累计收款不得超过应收余额。
  - 收款/付款单生成后立即生效，更新对应应收/应付的累计核销额与状态。
"""
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import IDMixin, TimestampMixin


class Receivable(IDMixin, TimestampMixin, Base):
    __tablename__ = "fin_receivable"

    receivable_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="应收单号 AR...")
    source_no: Mapped[str] = mapped_column(String(30), index=True, comment="来源单据号(发货单)")
    customer_id: Mapped[int] = mapped_column(ForeignKey("md_customer.id"), comment="客户")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="应收金额")
    received_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="已收金额")
    status: Mapped[str] = mapped_column(
        String(10), default="open", index=True,
        comment="状态: open/partial/settled",
    )
    due_date: Mapped[str | None] = mapped_column(Date, comment="到期日")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="生成人")

    customer: Mapped["Customer"] = relationship()
    receipts: Mapped[list["Receipt"]] = relationship(back_populates="receivable")


class Payable(IDMixin, TimestampMixin, Base):
    __tablename__ = "fin_payable"

    payable_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="应付单号 AP...")
    source_no: Mapped[str] = mapped_column(String(30), index=True, comment="来源单据号(入库单)")
    supplier_id: Mapped[int] = mapped_column(ForeignKey("md_supplier.id"), comment="供应商")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="应付金额")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, comment="已付金额")
    status: Mapped[str] = mapped_column(
        String(10), default="open", index=True,
        comment="状态: open/partial/settled",
    )
    due_date: Mapped[str | None] = mapped_column(Date, comment="到期日")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="生成人")

    supplier: Mapped["Supplier"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="payable")


class Receipt(IDMixin, TimestampMixin, Base):
    """收款单：核销一笔应收。"""

    __tablename__ = "fin_receipt"

    receipt_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="收款单号 RC...")
    receivable_id: Mapped[int] = mapped_column(ForeignKey("fin_receivable.id"), comment="应收单ID")
    receivable_no: Mapped[str] = mapped_column(String(30), comment="应收单号")
    customer_id: Mapped[int] = mapped_column(ForeignKey("md_customer.id"), comment="客户")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="收款金额")
    pay_method: Mapped[str] = mapped_column(String(10), default="bank", comment="方式: cash/bank/transfer")
    received_at: Mapped[str | None] = mapped_column(Date, comment="收款日期")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="操作人")

    receivable: Mapped["Receivable"] = relationship(back_populates="receipts")


class Payment(IDMixin, TimestampMixin, Base):
    """付款单：核销一笔应付。"""

    __tablename__ = "fin_payment"

    payment_no: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment="付款单号 PY...")
    payable_id: Mapped[int] = mapped_column(ForeignKey("fin_payable.id"), comment="应付单ID")
    payable_no: Mapped[str] = mapped_column(String(30), comment="应付单号")
    supplier_id: Mapped[int] = mapped_column(ForeignKey("md_supplier.id"), comment="供应商")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="付款金额")
    pay_method: Mapped[str] = mapped_column(String(10), default="bank", comment="方式: cash/bank/transfer")
    paid_at: Mapped[str | None] = mapped_column(Date, comment="付款日期")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_by: Mapped[str] = mapped_column(String(50), comment="操作人")

    payable: Mapped["Payable"] = relationship(back_populates="payments")