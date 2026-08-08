"""财务接口：应收、应付、收款单、付款单。"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..deps import require_permission
from ..models import Payable, Payment, Receipt, Receivable
from ..services.finance import create_payment as create_payment_svc, create_receipt as create_receipt_svc
from ..utils import fail, ok
from ..utils.pagination import paginate

router = APIRouter(prefix="/api/finance", tags=["财务管理"])

STATUS_TEXT = {"open": "未核销", "partial": "部分核销", "settled": "已核销"}


def _receivable_row(r: Receivable) -> dict:
    return {
        "id": r.id, "receivable_no": r.receivable_no, "source_no": r.source_no,
        "customer_id": r.customer_id,
        "customer_name": r.customer.name if r.customer else None,
        "total_amount": float(r.total_amount), "received_amount": float(r.received_amount),
        "balance": float(r.total_amount - r.received_amount),
        "status": r.status, "status_text": STATUS_TEXT.get(r.status, r.status),
        "due_date": str(r.due_date) if r.due_date else None,
        "remark": r.remark, "created_by": r.created_by, "created_at": str(r.created_at),
    }


def _payable_row(p: Payable) -> dict:
    return {
        "id": p.id, "payable_no": p.payable_no, "source_no": p.source_no,
        "supplier_id": p.supplier_id,
        "supplier_name": p.supplier.name if p.supplier else None,
        "total_amount": float(p.total_amount), "paid_amount": float(p.paid_amount),
        "balance": float(p.total_amount - p.paid_amount),
        "status": p.status, "status_text": STATUS_TEXT.get(p.status, p.status),
        "due_date": str(p.due_date) if p.due_date else None,
        "remark": p.remark, "created_by": p.created_by, "created_at": str(p.created_at),
    }


# ---------- 应收 ----------


@router.get("/receivables")
def list_receivables(
    status: str = "", keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("finance:read")),
):
    q = db.query(Receivable)
    if status:
        q = q.filter(Receivable.status == status)
    if keyword:
        q = q.filter(or_(Receivable.receivable_no.like(f"%{keyword}%"), Receivable.source_no.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(Receivable.id.desc()), page, page_size)
    result["items"] = [_receivable_row(r) for r in result["items"]]
    return ok(result)


# ---------- 应付 ----------


@router.get("/payables")
def list_payables(
    status: str = "", keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("finance:read")),
):
    q = db.query(Payable)
    if status:
        q = q.filter(Payable.status == status)
    if keyword:
        q = q.filter(or_(Payable.payable_no.like(f"%{keyword}%"), Payable.source_no.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(Payable.id.desc()), page, page_size)
    result["items"] = [_payable_row(p) for p in result["items"]]
    return ok(result)


# ---------- 收款单 ----------


class ReceiptBody(BaseModel):
    receivable_id: int
    amount: float = Field(gt=0)
    pay_method: str = "bank"
    received_at: str | None = None
    remark: str | None = None


@router.get("/receipts")
def list_receipts(
    keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("finance:read")),
):
    q = db.query(Receipt)
    if keyword:
        q = q.filter(Receipt.receipt_no.like(f"%{keyword}%"))
    result = paginate(db, q.order_by(Receipt.id.desc()), page, page_size)
    result["items"] = [
        {
            "id": r.id, "receipt_no": r.receipt_no, "receivable_no": r.receivable_no,
            "customer_name": r.receivable.customer.name if r.receivable else None,
            "amount": float(r.amount), "pay_method": r.pay_method,
            "received_at": str(r.received_at) if r.received_at else None,
            "remark": r.remark, "created_by": r.created_by, "created_at": str(r.created_at),
        }
        for r in result["items"]
    ]
    return ok(result)


@router.post("/receipts")
def create_receipt(
    body: ReceiptBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("finance:manage")),
):
    r = create_receipt_svc(db, body.model_dump(), op.username)
    write_audit(db, op.username, "pay", "finance", target=r.receipt_no,
                detail={"receivable_no": r.receivable_no, "amount": str(r.amount)}, ip=request.client.host)
    db.commit()
    return ok({"receipt_no": r.receipt_no}, "收款登记成功")


# ---------- 付款单 ----------


class PaymentBody(BaseModel):
    payable_id: int
    amount: float = Field(gt=0)
    pay_method: str = "bank"
    paid_at: str | None = None
    remark: str | None = None


@router.get("/payments")
def list_payments(
    keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("finance:read")),
):
    q = db.query(Payment)
    if keyword:
        q = q.filter(Payment.payment_no.like(f"%{keyword}%"))
    result = paginate(db, q.order_by(Payment.id.desc()), page, page_size)
    result["items"] = [
        {
            "id": p.id, "payment_no": p.payment_no, "payable_no": p.payable_no,
            "supplier_name": p.payable.supplier.name if p.payable else None,
            "amount": float(p.amount), "pay_method": p.pay_method,
            "paid_at": str(p.paid_at) if p.paid_at else None,
            "remark": p.remark, "created_by": p.created_by, "created_at": str(p.created_at),
        }
        for p in result["items"]
    ]
    return ok(result)


@router.post("/payments")
def create_payment(
    body: PaymentBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("finance:manage")),
):
    p = create_payment_svc(db, body.model_dump(), op.username)
    write_audit(db, op.username, "pay", "finance", target=p.payment_no,
                detail={"payable_no": p.payable_no, "amount": str(p.amount)}, ip=request.client.host)
    db.commit()
    return ok({"payment_no": p.payment_no}, "付款登记成功")