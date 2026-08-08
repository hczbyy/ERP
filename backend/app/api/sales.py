"""销售接口：销售订单全生命周期 + 发货出库单。"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..deps import require_permission
from ..models import SalesOrder, SalesOrderItem, StockOut, StockOutItem
from ..services.sales import (
    approve_sales_order, cancel_sales_order, create_sales_order, ship_sales,
)
from ..utils import fail, ok
from ..utils.pagination import paginate

router = APIRouter(prefix="/api/sales", tags=["销售管理"])

STATUS_TEXT = {
    "draft": "草稿", "approved": "已审核", "partially_shipped": "部分发货",
    "completed": "已完成", "cancelled": "已取消",
}


class OrderItemBody(BaseModel):
    product_id: int
    qty: float = Field(gt=0)
    price: float = Field(ge=0)


class OrderBody(BaseModel):
    customer_id: int
    warehouse_id: int
    remark: str | None = None
    items: list[OrderItemBody]


class CancelBody(BaseModel):
    reason: str | None = None


class ShipBody(BaseModel):
    remark: str | None = None
    items: list[OrderItemBody]


def _order_row(o: SalesOrder) -> dict:
    return {
        "id": o.id, "order_no": o.order_no,
        "customer_id": o.customer_id,
        "customer_name": o.customer.name if o.customer else None,
        "warehouse_id": o.warehouse_id,
        "warehouse_name": o.warehouse.name if o.warehouse else None,
        "status": o.status, "status_text": STATUS_TEXT.get(o.status, o.status),
        "total_amount": float(o.total_amount), "remark": o.remark,
        "approved_by": o.approved_by, "approved_at": o.approved_at,
        "created_by": o.created_by, "cancel_reason": o.cancel_reason,
        "created_at": str(o.created_at),
    }


def _item_row(it: SalesOrderItem) -> dict:
    return {
        "id": it.id, "product_id": it.product_id,
        "product_code": it.product.code if it.product else None,
        "product_name": it.product.name if it.product else None,
        "unit": it.product.unit if it.product else None,
        "qty": float(it.qty), "price": float(it.price), "amount": float(it.amount),
        "shipped_qty": float(it.shipped_qty),
        "remain_qty": float(it.qty - it.shipped_qty),
    }


def _stock_out_row(so: StockOut) -> dict:
    return {
        "id": so.id, "stock_out_no": so.stock_out_no, "so_no": so.so_no,
        "customer_name": so.customer.name if so.customer else None,
        "warehouse_name": so.warehouse.name if so.warehouse else None,
        "total_amount": float(so.total_amount), "remark": so.remark,
        "created_by": so.created_by, "created_at": str(so.created_at),
    }


@router.get("/orders")
def list_orders(
    status: str = "", keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("sales:order:read")),
):
    q = db.query(SalesOrder)
    if status:
        q = q.filter(SalesOrder.status == status)
    if keyword:
        q = q.filter(or_(SalesOrder.order_no.like(f"%{keyword}%"), SalesOrder.remark.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(SalesOrder.id.desc()), page, page_size)
    result["items"] = [_order_row(o) for o in result["items"]]
    return ok(result)


@router.get("/orders/{order_id}")
def order_detail(
    order_id: int,
    db: Session = Depends(get_db), _=Depends(require_permission("sales:order:read")),
):
    o = db.get(SalesOrder, order_id)
    if not o:
        return fail("销售单不存在")
    data = _order_row(o)
    data["items"] = [_item_row(it) for it in o.items]
    return ok(data)


@router.post("/orders")
def create_order(
    body: OrderBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("sales:order:manage")),
):
    o = create_sales_order(db, body.model_dump(), op.username)
    write_audit(db, op.username, "create", "sales", target=o.order_no,
                detail={"customer_id": body.customer_id, "amount": str(o.total_amount)}, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "销售单创建成功")


@router.put("/orders/{order_id}")
def update_order(
    order_id: int, body: OrderBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("sales:order:manage")),
):
    o = db.get(SalesOrder, order_id)
    if not o:
        return fail("销售单不存在")
    if o.status != "draft":
        return fail(f"仅草稿状态可修改，当前状态: {STATUS_TEXT.get(o.status)}")
    o.customer_id, o.warehouse_id, o.remark = body.customer_id, body.warehouse_id, body.remark
    o.items.clear()
    total = 0
    for it in body.items:
        amount = round(it.qty * it.price, 2)
        total += amount
        o.items.append(
            SalesOrderItem(product_id=it.product_id, qty=it.qty, price=it.price, amount=amount)
        )
    o.total_amount = round(total, 2)
    write_audit(db, op.username, "update", "sales", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "销售单已更新")


@router.post("/orders/{order_id}/approve")
def approve_order(
    order_id: int, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("sales:order:manage")),
):
    o = db.get(SalesOrder, order_id)
    if not o:
        return fail("销售单不存在")
    approve_sales_order(db, o, op.username)
    write_audit(db, op.username, "approve", "sales", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "审核成功")


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int, body: CancelBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("sales:order:manage")),
):
    o = db.get(SalesOrder, order_id)
    if not o:
        return fail("销售单不存在")
    cancel_sales_order(db, o, op.username, body.reason or "")
    write_audit(db, op.username, "cancel", "sales", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(_order_row(o), "已取消")


@router.post("/orders/{order_id}/ship")
def ship_order(
    order_id: int, body: ShipBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("sales:ship:manage")),
):
    """发货出库：生成出库单 + 库存扣减 + 应收挂账。"""
    o = db.get(SalesOrder, order_id)
    if not o:
        return fail("销售单不存在")
    so = ship_sales(db, o, body.model_dump(), op.username)
    write_audit(db, op.username, "ship", "sales", target=so.stock_out_no,
                detail={"so_no": o.order_no, "amount": str(so.total_amount)}, ip=request.client.host)
    db.commit()
    return ok({"stock_out_no": so.stock_out_no, "total_amount": float(so.total_amount)}, "发货成功")


@router.delete("/orders/{order_id}")
def delete_order(
    order_id: int, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("sales:order:manage")),
):
    o = db.get(SalesOrder, order_id)
    if not o:
        return fail("销售单不存在")
    if o.status != "draft":
        return fail("仅草稿状态可删除")
    db.delete(o)
    write_audit(db, op.username, "delete", "sales", target=o.order_no, ip=request.client.host)
    db.commit()
    return ok(message="销售单已删除")


# ---------- 出库单 ----------


@router.get("/stock-outs")
def list_stock_outs(
    keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("sales:order:read")),
):
    q = db.query(StockOut)
    if keyword:
        q = q.filter(or_(StockOut.stock_out_no.like(f"%{keyword}%"), StockOut.so_no.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(StockOut.id.desc()), page, page_size)
    result["items"] = [_stock_out_row(so) for so in result["items"]]
    return ok(result)


@router.get("/stock-outs/{so_id}")
def stock_out_detail(
    so_id: int,
    db: Session = Depends(get_db), _=Depends(require_permission("sales:order:read")),
):
    so = db.get(StockOut, so_id)
    if not so:
        return fail("出库单不存在")
    data = _stock_out_row(so)
    data["items"] = [
        {
            "product_code": it.product.code if it.product else None,
            "product_name": it.product.name if it.product else None,
            "qty": float(it.qty), "price": float(it.price), "amount": float(it.amount),
        }
        for it in so.items
    ]
    return ok(data)