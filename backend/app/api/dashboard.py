"""仪表盘与报表接口。"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_permission
from ..models import (
    Payable, Product, PurchaseOrder, Receivable, SalesOrder, Stock,
    StockLog, StockOut, StockOutItem,
)
from ..utils import ok

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _=Depends(require_permission("dashboard:view"))):
    today = date.today().isoformat()

    today_sales = float(
        db.query(func.coalesce(func.sum(StockOut.total_amount), 0))
        .filter(func.date(StockOut.created_at) == today)
        .scalar()
    )
    today_orders = db.query(func.count(SalesOrder.id)).filter(func.date(SalesOrder.created_at) == today).scalar()
    pending_approve = (
        db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.status == "draft").scalar()
        + db.query(func.count(SalesOrder.id)).filter(SalesOrder.status == "draft").scalar()
    )
    low_stocks = db.query(func.count(Stock.id)).join(Product, Stock.product_id == Product.id).filter(
        Stock.qty < Product.safety_stock
    ).scalar()
    receivable_balance = float(
        db.query(func.coalesce(func.sum(Receivable.total_amount - Receivable.received_amount), 0))
        .filter(Receivable.status != "settled").scalar()
    )
    payable_balance = float(
        db.query(func.coalesce(func.sum(Payable.total_amount - Payable.paid_amount), 0))
        .filter(Payable.status != "settled").scalar()
    )
    return ok({
        "today_sales": today_sales,
        "today_orders": today_orders or 0,
        "pending_approve": pending_approve,
        "low_stocks": low_stocks or 0,
        "receivable_balance": receivable_balance,
        "payable_balance": payable_balance,
    })


@router.get("/sales-trend")
def sales_trend(
    days: int = 7,
    db: Session = Depends(get_db), _=Depends(require_permission("dashboard:view")),
):
    """近 N 天每日销售金额与订单数。"""
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = (
        db.query(
            func.date(StockOut.created_at).label("d"),
            func.coalesce(func.sum(StockOut.total_amount), 0).label("amount"),
        )
        .filter(func.date(StockOut.created_at) >= start)
        .group_by("d")
        .order_by("d")
        .all()
    )
    amount_map = {r.d: float(r.amount) for r in rows}

    order_rows = (
        db.query(
            func.date(SalesOrder.created_at).label("d"),
            func.count(SalesOrder.id).label("cnt"),
        )
        .filter(func.date(SalesOrder.created_at) >= start)
        .group_by("d")
        .all()
    )
    order_map = {r.d: r.cnt for r in order_rows}

    labels, amounts, counts = [], [], []
    for i in range(days):
        d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        labels.append(d)
        amounts.append(amount_map.get(d, 0))
        counts.append(order_map.get(d, 0))
    return ok({"labels": labels, "amounts": amounts, "counts": counts})


@router.get("/top-products")
def top_products(
    limit: int = 5,
    db: Session = Depends(get_db), _=Depends(require_permission("dashboard:view")),
):
    """销量 TOP N 商品（按出库明细聚合）。"""
    rows = (
        db.query(
            Product.name.label("name"),
            func.coalesce(func.sum(StockOutItem.qty), 0).label("qty"),
            func.coalesce(func.sum(StockOutItem.amount), 0).label("amount"),
        )
        .join(StockOutItem, StockOutItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(func.sum(StockOutItem.qty).desc())
        .limit(limit)
        .all()
    )
    return ok([{"name": r.name, "qty": float(r.qty), "amount": float(r.amount)} for r in rows])


@router.get("/low-stocks")
def low_stocks(
    limit: int = 10,
    db: Session = Depends(get_db), _=Depends(require_permission("dashboard:view")),
):
    """库存预警列表。"""
    rows = (
        db.query(Product.name, Stock.qty, Product.safety_stock, Product.code)
        .join(Stock, Stock.product_id == Product.id)
        .filter(Stock.qty < Product.safety_stock)
        .order_by((Stock.qty - Product.safety_stock))
        .limit(limit)
        .all()
    )
    return ok(
        [
            {"code": r.code, "name": r.name, "qty": float(r.qty), "safety_stock": float(r.safety_stock)}
            for r in rows
        ]
    )


@router.get("/recent-orders")
def recent_orders(
    limit: int = 8,
    db: Session = Depends(get_db), _=Depends(require_permission("dashboard:view")),
):
    """最近销售订单（首页列表）。"""
    rows = (
        db.query(SalesOrder)
        .order_by(SalesOrder.id.desc())
        .limit(limit)
        .all()
    )
    return ok(
        [
            {
                "order_no": o.order_no,
                "customer_name": o.customer.name if o.customer else None,
                "total_amount": float(o.total_amount),
                "status": o.status,
                "created_at": str(o.created_at),
            }
            for o in rows
        ]
    )