"""采购接口：采购订单全生命周期 + 收货入库单。"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..deps import require_permission
from ..models import PurchaseOrder, PurchaseOrderItem, StockIn, StockInItem
from ..services.purchase import (
    approve_purchase_order, cancel_purchase_order, create_purchase_order, receive_purchase,
)
from ..utils import fail, ok
from ..utils.pagination import paginate

router = APIRouter(prefix="/api/purchase", tags=["采购管理"])

STATUS_TEXT = {
    "draft": "草稿", "approved": "已审核", "partially_received": "部分收货",
    "completed": "已完成", "cancelled": "已取消",
}


class OrderItemBody(BaseModel):
    product_id: int
    qty: float = Field(gt=0)
    price: float = Field(ge=0)


class OrderBody(BaseModel):
    supplier_id: int
    warehouse_id: int
    remark: str | None = None
    items: list[OrderItemBody]


class CancelBody(BaseModel):
    reason: str | None = None


class ReceiveBody(BaseModel):
    remark: str | None = None
    items: list[OrderItemBody]


def _order_row(o: PurchaseOrder) -> dict:
    return {
        "id": o.id, "order_no": o.order_no,
        "supplier_id": o.supplier_id,
        "supplier_name": o.supplier.name if o.supplier else None,
        "warehouse_id": o.warehouse_id,
        "warehouse_name": o.warehouse.name if o.warehouse else None,
        "status": o.status, "status_text": STATUS_TEXT.get(o.status, o.status),
        "total_amount": float(o.total_amount), "remark": o.remark,
        "approved_by": o.approved_by, "approved_at": o.approved_at,
        "created_by": o.created_by, "cancel_reason": o.cancel_reason,
        "created_at": str(o.created_at),
    }


def _item_row(it: PurchaseOrderItem) -> dict:
    return {
        "id": it.id, "product_id": it.product_id,
        "product_code": it.product.code if it.product else None,
        "product_name": it.product.name if it.product else None,
        "unit": it.product.unit if it.product else None,
        "qty": float(it.qty), "price": float(it.price), "amount": float(it.amount),
        "received_qty": float(it.received_qty),
        "remain_qty": float(it.qty - it.received_qty),
    }


def _stock_in_row(si: StockIn) -> dict:
    return {
        "id": si.id, "stock_in_no": si.stock_in_no, "po_no": si.po_no,
        "supplier_name": si.supplier.name if si.supplier else None,
        "warehouse_name": si.warehouse.name if si.warehouse else None,
        "total_amount": float(si.total_amount), "remark": si.remark,
        "created_by": si.created_by, "created_at": str(si.created_at),
    }


@router.get("/orders")
def list_orders(
    status: str = "", keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("purchase:order:read")),
):
    q = db.query(PurchaseOrder)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    if keyword:
        q = q.filter(or_(PurchaseOrder.order_no.like(f"%{keyword}%"), PurchaseOrder.remark.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(PurchaseOrder.id.desc()), page, page_size)
    result["items"] = [_order_row(o) for o in result["items"]]
    return ok(result)


@router.get("/orders/{order_id}")
def order_detail(
    order_id: int,
    db: Session = Depends(get_db), _=Depends(require_permission("purchase:order:read")),
):
    o = db.get(PurchaseOrder, order_id)
    if not o:
        return fail("采购单不存在")
    data = _order_row(o)
    data["items"] = [_item_row(it) for it in o.items]
    return ok(data)


@router.post("/orders")
def create_order(
    body: OrderBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("purchase:order:manage")),
):
    o = create_purchase_order(db, body.model_dump(), op.username)
    write_audit(db, op.username, "create", "purchase", target=o.order_no,
                detail={"supplier_id": body.supplier_id, "amount": str(o.total_amount)}, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "采购单创建成功")


@router.put("/orders/{order_id}")
def update_order(
    order_id: int, body: OrderBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("purchase:order:manage")),
):
    o = db.get(PurchaseOrder, order_id)
    if not o:
        return fail("采购单不存在")
    if o.status != "draft":
        return fail(f"仅草稿状态可修改，当前状态: {STATUS_TEXT.get(o.status)}")
    o.supplier_id, o.warehouse_id, o.remark = body.supplier_id, body.warehouse_id, body.remark
    o.items.clear()
    total = 0
    for it in body.items:
        amount = round(it.qty * it.price, 2)
        total += amount
        o.items.append(
            PurchaseOrderItem(product_id=it.product_id, qty=it.qty, price=it.price, amount=amount)
        )
    o.total_amount = round(total, 2)
    write_audit(db, op.username, "update", "purchase", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "采购单已更新")


@router.post("/orders/{order_id}/approve")
def approve_order(
    order_id: int, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("purchase:order:manage")),
):
    o = db.get(PurchaseOrder, order_id)
    if not o:
        return fail("采购单不存在")
    approve_purchase_order(db, o, op.username)
    write_audit(db, op.username, "approve", "purchase", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "审核成功")


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int, body: CancelBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("purchase:order:manage")),
):
    o = db.get(PurchaseOrder, order_id)
    if not o:
        return fail("采购单不存在")
    cancel_purchase_order(db, o, op.username, body.reason or "")
    write_audit(db, op.username, "cancel", "purchase", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "已取消")


@router.post("/orders/{order_id}/receive")
def receive_order(
    order_id: int, body: ReceiveBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("purchase:receive:manage")),
):
    """收货入库：生成入库单 + 库存增加 + 应付挂账。"""
    o = db.get(PurchaseOrder, order_id)
    if not o:
        return fail("采购单不存在")
    si = receive_purchase(db, o, body.model_dump(), op.username)
    write_audit(db, op.username, "receive", "purchase", target=si.stock_in_no,
                detail={"po_no": o.order_no, "amount": str(si.total_amount)}, ip=request.client.host)
    db.commit()
    return ok({"stock_in_no": si.stock_in_no, "total_amount": float(si.total_amount)}, "收货入库成功")


@router.delete("/orders/{order_id}")
def delete_order(
    order_id: int, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("purchase:order:manage")),
):
    o = db.get(PurchaseOrder, order_id)
    if not o:
        return fail("采购单不存在")
    if o.status != "draft":
        return fail("仅草稿状态可删除")
    db.delete(o)
    write_audit(db, op.username, "delete", "purchase", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(message="采购单已删除")


# ---------- 入库单 ----------


@router.get("/stock-ins")
def list_stock_ins(
    keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("purchase:order:read")),
):
    q = db.query(StockIn)
    if keyword:
        q = q.filter(or_(StockIn.stock_in_no.like(f"%{keyword}%"), StockIn.po_no.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(StockIn.id.desc()), page, page_size)
    result["items"] = [_stock_in_row(si) for si in result["items"]]
    return ok(result)


@router.get("/stock-ins/{si_id}")
def stock_in_detail(
    si_id: int,
    db: Session = Depends(get_db), _=Depends(require_permission("purchase:order:read")),
):
    si = db.get(StockIn, si_id)
    if not si:
        return fail("入库单不存在")
    data = _stock_in_row(si)
    data["items"] = [
        {
            "product_code": it.product.code if it.product else None,
            "product_name": it.product.name if it.product else None,
            "qty": float(it.qty), "price": float(it.price), "amount": float(it.amount),
        }
        for it in si.items
    ]
    return ok(data)