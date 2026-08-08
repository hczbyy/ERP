"""财务服务：收款核销应收、付款核销应付。"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import Payable, Payment, Receipt, Receivable
from ..utils import BusinessError
from .bill_no import gen_bill_no


def create_receipt(db: Session, data: dict, username: str) -> Receipt:
    """对一笔应收收款。金额必须大于0且不超过应收余额。"""
    receivable = db.get(Receivable, data["receivable_id"])
    if not receivable:
        raise BusinessError("应收单不存在")
    amount = Decimal(data["amount"])
    balance = receivable.total_amount - receivable.received_amount
    if amount <= 0:
        raise BusinessError("收款金额必须大于0")
    if amount > balance:
        raise BusinessError(f"收款金额 {amount} 超过应收余额 {balance}")

    receipt = Receipt(
        receipt_no=gen_bill_no(db, "receipt"),
        receivable_id=receivable.id,
        receivable_no=receivable.receivable_no,
        customer_id=receivable.customer_id,
        amount=amount,
        pay_method=data.get("pay_method", "bank"),
        received_at=data.get("received_at") or date.today(),
        remark=data.get("remark"),
        created_by=username,
    )
    receivable.received_amount += amount
    receivable.status = (
        "settled"
        if receivable.received_amount >= receivable.total_amount
        else "partial"
    )
    db.add(receipt)
    db.flush()
    return receipt


def create_payment(db: Session, data: dict, username: str) -> Payment:
    """对一笔应付付款。金额必须大于0且不超过应付余额。"""
    payable = db.get(Payable, data["payable_id"])
    if not payable:
        raise BusinessError("应付单不存在")
    amount = Decimal(data["amount"])
    balance = payable.total_amount - payable.paid_amount
    if amount <= 0:
        raise BusinessError("付款金额必须大于0")
    if amount > balance:
        raise BusinessError(f"付款金额 {amount} 超过应付余额 {balance}")

    payment = Payment(
        payment_no=gen_bill_no(db, "payment"),
        payable_id=payable.id,
        payable_no=payable.payable_no,
        supplier_id=payable.supplier_id,
        amount=amount,
        pay_method=data.get("pay_method", "bank"),
        paid_at=data.get("paid_at") or date.today(),
        remark=data.get("remark"),
        created_by=username,
    )
    payable.paid_amount += amount
    payable.status = "settled" if payable.paid_amount >= payable.total_amount else "partial"
    db.add(payment)
    db.flush()
    return payment