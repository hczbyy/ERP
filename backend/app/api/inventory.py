"""库存接口：库存查询、流水、盘点、调拨。"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..deps import require_permission
from ..models import (
    Product, Stock, StockCheck, StockCheckItem, StockLog, StockTransfer, StockTransferItem, Warehouse,
)
from ..services.bill_no import gen_bill_no
from ..services.inventory import change_stock
from ..utils import fail, ok
from ..utils.pagination import paginate

router = APIRouter(prefix="/api/inventory", tags=["库存管理"])

LOG_TYPE_TEXT = {
    "purchase_in": "采购入库", "sale_out": "销售出库",
    "transfer_in": "调拨入库", "transfer_out": "调拨出库",
    "check_in": "盘盈调整", "check_out": "盘亏调整", "initial": "期初建账",
}


# ---------- 库存查询 ----------


@router.get("/stocks")
def list_stocks(
    keyword: str = "", warehouse_id: int | None = None,
    low_stock_only: bool = False, page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("inventory:stock:read")),
):
    q = db.query(Stock, Product).join(Product, Stock.product_id == Product.id)
    if warehouse_id:
        q = q.filter(Stock.warehouse_id == warehouse_id)
    if keyword:
        q = q.filter(or_(Product.name.like(f"%{keyword}%"), Product.code.like(f"%{keyword}%")))
    if low_stock_only:
        q = q.filter(Stock.qty < Product.safety_stock)
    result = paginate(db, q.order_by(Stock.id.desc()), page, page_size)
    wh_map = {w.id: w.name for w in db.query(Warehouse).all()}
    items = []
    for s, p in result["items"]:
        items.append({
            "id": s.id, "product_id": p.id, "product_code": p.code,
            "product_name": p.name, "unit": p.unit,
            "warehouse_id": s.warehouse_id, "warehouse_name": wh_map.get(s.warehouse_id),
            "qty": float(s.qty), "safety_stock": float(p.safety_stock),
            "is_low": float(s.qty) < float(p.safety_stock),
        })
    result["items"] = items
    return ok(result)


@router.get("/logs")
def list_logs(
    product_id: int | None = None, warehouse_id: int | None = None,
    log_type: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("inventory:stock:read")),
):
    q = db.query(StockLog)
    if product_id:
        q = q.filter(StockLog.product_id == product_id)
    if warehouse_id:
        q = q.filter(StockLog.warehouse_id == warehouse_id)
    if log_type:
        q = q.filter(StockLog.log_type == log_type)
    result = paginate(db, q.order_by(StockLog.id.desc()), page, page_size)
    wh_map = {w.id: w.name for w in db.query(Warehouse).all()}
    p_map = {p.id: p for p in db.query(Product).all()}
    result["items"] = [
        {
            "id": l.id,
            "product_code": p_map[l.product_id].code if l.product_id in p_map else None,
            "product_name": p_map[l.product_id].name if l.product_id in p_map else None,
            "warehouse_name": wh_map.get(l.warehouse_id),
            "change_qty": float(l.change_qty), "before_qty": float(l.before_qty),
            "after_qty": float(l.after_qty), "log_type": l.log_type,
            "log_type_text": LOG_TYPE_TEXT.get(l.log_type, l.log_type),
            "ref_no": l.ref_no, "remark": l.remark, "created_by": l.created_by,
            "created_at": str(l.created_at),
        }
        for l in result["items"]
    ]
    return ok(result)


# ---------- 盘点 ----------


class CheckCreateBody(BaseModel):
    warehouse_id: int
    remark: str | None = None
    product_ids: list[int] = Field(min_length=1)


class CheckItemBody(BaseModel):
    product_id: int
    actual_qty: float = Field(ge=0)


class CheckUpdateBody(BaseModel):
    items: list[CheckItemBody]


def _check_row(db: Session, c: StockCheck, with_items: bool = False) -> dict:
    data = {
        "id": c.id, "check_no": c.check_no, "warehouse_id": c.warehouse_id,
        "warehouse_name": c.warehouse.name if c.warehouse else None,
        "status": c.status, "remark": c.remark, "created_by": c.created_by,
        "done_by": c.done_by, "done_at": c.done_at,
        "created_at": str(c.created_at),
    }
    if with_items:
        p_map = {p.id: p for p in db.query(Product).all()}
        data["items"] = [
            {
                "product_id": it.product_id,
                "product_code": p_map[it.product_id].code if it.product_id in p_map else None,
                "product_name": p_map[it.product_id].name if it.product_id in p_map else None,
                "unit": p_map[it.product_id].unit if it.product_id in p_map else None,
                "book_qty": float(it.book_qty), "actual_qty": float(it.actual_qty),
                "diff_qty": float(it.diff_qty),
            }
            for it in c.items
        ]
    return data


@router.get("/checks")
def list_checks(
    status: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("inventory:manage")),
):
    q = db.query(StockCheck)
    if status:
        q = q.filter(StockCheck.status == status)
    result = paginate(db, q.order_by(StockCheck.id.desc()), page, page_size)
    result["items"] = [_check_row(db, c) for c in result["items"]]
    return ok(result)


@router.get("/checks/{check_id}")
def check_detail(
    check_id: int,
    db: Session = Depends(get_db), _=Depends(require_permission("inventory:manage")),
):
    c = db.get(StockCheck, check_id)
    if not c:
        return fail("盘点单不存在")
    return ok(_check_row(db, c, with_items=True))


@router.post("/checks")
def create_check(
    body: CheckCreateBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("inventory:manage")),
):
    c = StockCheck(
        check_no=gen_bill_no(db, "stock_check"),
        warehouse_id=body.warehouse_id,
        remark=body.remark,
        created_by=op.username,
    )
    for pid in body.product_ids:
        stock = db.query(Stock).filter_by(product_id=pid, warehouse_id=body.warehouse_id).first()
        book = stock.qty if stock else Decimal(0)
        c.items.append(StockCheckItem(product_id=pid, book_qty=book))
    db.add(c)
    db.flush()
    write_audit(db, op.username, "create", "inventory", target=c.check_no, ip=request.client.host)
    db.commit()
    return ok(_check_row(db, c, with_items=True), "盘点单创建成功")


@router.put("/checks/{check_id}")
def update_check(
    check_id: int, body: CheckUpdateBody,
    db: Session = Depends(get_db), op=Depends(require_permission("inventory:manage")),
):
    c = db.get(StockCheck, check_id)
    if not c:
        return fail("盘点单不存在")
    if c.status != "draft":
        return fail("仅草稿状态可录入实盘数量")
    item_map = {it.product_id: it for it in c.items}
    for it in body.items:
        item = item_map.get(it.product_id)
        if not item:
            return fail(f"商品 #{it.product_id} 不在盘点单中")
        item.actual_qty = Decimal(it.actual_qty)
        item.diff_qty = item.actual_qty - item.book_qty
    db.commit()
    return ok(_check_row(db, c, with_items=True), "实盘数量已保存")


@router.post("/checks/{check_id}/done")
def done_check(
    check_id: int, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("inventory:manage")),
):
    """提交盘点：按差异调整库存（盘盈入、盘亏出），生成调整流水。"""
    c = db.get(StockCheck, check_id)
    if not c:
        return fail("盘点单不存在")
    if c.status != "draft":
        return fail("盘点单已提交")
    for it in c.items:
        diff = it.actual_qty - it.book_qty
        if diff == 0:
            continue
        change_stock(
            db,
            product_id=it.product_id,
            warehouse_id=c.warehouse_id,
            delta=diff,
            log_type="check_in" if diff > 0 else "check_out",
            ref_no=c.check_no,
            created_by=op.username,
            remark=f"盘点调整({c.check_no})",
        )
    c.status = "done"
    c.done_by = op.username
    c.done_at = datetime.now().isoformat(timespec="seconds")
    write_audit(db, op.username, "check", "inventory", target=c.check_no, ip=request.client.host)
    db.commit()
    return ok(message="盘点完成，库存已调整")


# ---------- 调拨 ----------


class TransferItemBody(BaseModel):
    product_id: int
    qty: float = Field(gt=0)


class TransferBody(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    remark: str | None = None
    items: list[TransferItemBody] = Field(min_length=1)


def _transfer_row(t: StockTransfer) -> dict:
    return {
        "id": t.id, "transfer_no": t.transfer_no,
        "from_warehouse_id": t.from_warehouse_id,
        "from_warehouse_name": t.from_warehouse.name if t.from_warehouse else None,
        "to_warehouse_id": t.to_warehouse_id,
        "to_warehouse_name": t.to_warehouse.name if t.to_warehouse else None,
        "remark": t.remark, "created_by": t.created_by,
        "created_at": str(t.created_at),
    }


@router.get("/transfers")
def list_transfers(
    page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("inventory:manage")),
):
    result = paginate(db, db.query(StockTransfer).order_by(StockTransfer.id.desc()), page, page_size)
    result["items"] = [_transfer_row(t) for t in result["items"]]
    return ok(result)


@router.post("/transfers")
def create_transfer(
    body: TransferBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("inventory:manage")),
):
    if body.from_warehouse_id == body.to_warehouse_id:
        return fail("调出与调入仓库不能相同")
    t = StockTransfer(
        transfer_no=gen_bill_no(db, "stock_transfer"),
        from_warehouse_id=body.from_warehouse_id,
        to_warehouse_id=body.to_warehouse_id,
        remark=body.remark,
        created_by=op.username,
    )
    db.add(t)
    db.flush()
    for it in body.items:
        # 源仓库出
        change_stock(
            db, product_id=it.product_id, warehouse_id=body.from_warehouse_id,
            delta=-Decimal(it.qty), log_type="transfer_out", ref_no=t.transfer_no,
            created_by=op.username, remark=f"调拨至仓#{body.to_warehouse_id}",
        )
        # 目标仓库入
        change_stock(
            db, product_id=it.product_id, warehouse_id=body.to_warehouse_id,
            delta=Decimal(it.qty), log_type="transfer_in", ref_no=t.transfer_no,
            created_by=op.username, remark=f"自仓#{body.from_warehouse_id}调入",
        )
        t.items.append(StockTransferItem(product_id=it.product_id, qty=it.qty))
    write_audit(db, op.username, "transfer", "inventory", target=t.transfer_no, ip=request.client.host)
    db.commit()
    return ok(_transfer_row(t), "调拨成功")