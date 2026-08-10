"""销售订单服务：创建 / 审核 / 取消 / 发货出库。

状态机：draft -> approved -> partially_shipped -> completed
              \-> cancelled
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import Receivable, SalesOrder, SalesOrderItem, StockOut, StockOutItem
from ..utils import BusinessError
from .bill_no import gen_bill_no
from .inventory import change_stock, get_stock_qty


def create_sales_order(db: Session, data: dict, username: str) -> SalesOrder:
    items = data.get("items") or []
    if not items:
        raise BusinessError("销售单至少需要一条商品明细")

    order = SalesOrder(
        order_no=gen_bill_no(db, "sales_order"),
        customer_id=data["customer_id"],
        warehouse_id=data["warehouse_id"],
        remark=data.get("remark"),
        created_by=username,
    )
    total = Decimal(0)
    for it in items:
        qty = Decimal(it["qty"])
        price = Decimal(it["price"])
        if qty <= 0 or price < 0:
            raise BusinessError(f"商品 #{it['product_id']} 数量必须大于0，单价不能为负")
        amount = qty * price
        total += amount
        order.items.append(
            SalesOrderItem(product_id=it["product_id"], qty=qty, price=price, amount=amount)
        )
    order.total_amount = total
    db.add(order)
    db.flush()
    return order


def approve_sales_order(db: Session, order: SalesOrder, username: str) -> SalesOrder:
    if order.status != "draft":
        raise BusinessError(f"只有草稿状态的销售单才能审核，当前状态: {order.status}")
    order.status = "approved"
    order.approved_by = username
    order.approved_at = date.today().isoformat()
    return order


def cancel_sales_order(db: Session, order: SalesOrder, username: str, reason: str) -> SalesOrder:
    if order.status not in ("draft", "approved"):
        raise BusinessError(f"当前状态 {order.status} 不允许取消")
    order.status = "cancelled"
    order.cancel_reason = reason or "未说明"
    return order


def ship_sales(db: Session, order: SalesOrder, data: dict, username: str) -> StockOut:
    """按发货明细生成出库单：库存扣减(校验充足) + 应收挂账 + 销售单状态推进。"""
    if order.status not in ("approved", "partially_shipped"):
        raise BusinessError(f"只有已审核的销售单才能发货，当前状态: {order.status}")

    items = data.get("items") or []
    if not items:
        raise BusinessError("发货明细不能为空")
    item_map = {it.product_id: it for it in order.items}
    for it in items:
        qty = Decimal(it["qty"])
        if qty <= 0:
            raise BusinessError("发货数量必须大于0")
        price = Decimal(it.get("price", 0))
        if price < 0:
            raise BusinessError("发货单价不能为负")
        so_item = item_map.get(it["product_id"])
        if so_item is None:
            raise BusinessError(f"商品 #{it['product_id']} 不在销售单中")
        remain = so_item.qty - so_item.shipped_qty
        if qty > remain:
            raise BusinessError(f"商品「{so_item.product.name}」发货数量 {qty} 超过未发数量 {remain}")
        # 库存充足校验
        stock_qty = get_stock_qty(db, it["product_id"], order.warehouse_id)
        if qty > stock_qty:
            raise BusinessError(
                f"商品「{so_item.product.name}」库存不足：当前 {stock_qty}，需要 {qty}"
            )

    stock_out = StockOut(
        stock_out_no=gen_bill_no(db, "stock_out"),
        so_id=order.id,
        so_no=order.order_no,
        customer_id=order.customer_id,
        warehouse_id=order.warehouse_id,
        remark=data.get("remark"),
        created_by=username,
    )
    total = Decimal(0)
    for it in items:
        qty = Decimal(it["qty"])
        so_item = item_map[it["product_id"]]
        price = Decimal(it["price"])  # 按实际发货单价入账（前端默认带销售单价）
        amount = qty * price
        total += amount
        so_item.shipped_qty += qty
        stock_out.items.append(
            StockOutItem(product_id=it["product_id"], qty=qty, price=price, amount=amount)
        )
        change_stock(
            db,
            product_id=it["product_id"],
            warehouse_id=order.warehouse_id,
            delta=-qty,
            log_type="sale_out",
            ref_no=stock_out.stock_out_no,
            created_by=username,
            remark=f"销售出库 {order.order_no}",
        )
    stock_out.total_amount = total
    db.add(stock_out)
    db.flush()

    # 挂应收（按实际发货金额）
    db.add(
        Receivable(
            receivable_no=gen_bill_no(db, "receivable"),
            source_no=stock_out.stock_out_no,
            customer_id=order.customer_id,
            total_amount=total,
            due_date=date.today(),
            remark=f"销售出库 {order.order_no}",
            created_by=username,
        )
    )

    if all(item.shipped_qty >= item.qty for item in order.items):
        order.status = "completed"
    else:
        order.status = "partially_shipped"
    return stock_out