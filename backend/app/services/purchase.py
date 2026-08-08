"""采购订单服务：创建 / 审核 / 取消 / 收货入库。

状态机：draft -> approved -> partially_received -> completed
              \-> cancelled
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import Payable, PurchaseOrder, PurchaseOrderItem, StockIn, StockInItem
from ..utils import BusinessError
from .bill_no import gen_bill_no
from .inventory import change_stock

VALID_STATUS = {"draft", "approved", "partially_received", "completed", "cancelled"}


def create_purchase_order(db: Session, data: dict, username: str) -> PurchaseOrder:
    items = data.get("items") or []
    if not items:
        raise BusinessError("采购单至少需要一条商品明细")

    order = PurchaseOrder(
        order_no=gen_bill_no(db, "purchase_order"),
        supplier_id=data["supplier_id"],
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
            PurchaseOrderItem(
                product_id=it["product_id"], qty=qty, price=price, amount=amount
            )
        )
    order.total_amount = total
    db.add(order)
    db.flush()
    return order


def approve_purchase_order(db: Session, order: PurchaseOrder, username: str) -> PurchaseOrder:
    if order.status != "draft":
        raise BusinessError(f"只有草稿状态的采购单才能审核，当前状态: {order.status}")
    order.status = "approved"
    order.approved_by = username
    order.approved_at = date.today().isoformat()
    return order


def cancel_purchase_order(db: Session, order: PurchaseOrder, username: str, reason: str) -> PurchaseOrder:
    if order.status not in ("draft", "approved"):
        raise BusinessError(f"当前状态 {order.status} 不允许取消")
    order.status = "cancelled"
    order.cancel_reason = reason or "未说明"
    return order


def receive_purchase(db: Session, order: PurchaseOrder, data: dict, username: str) -> StockIn:
    """按收货明细生成入库单：库存增加 + 应付挂账 + 采购单状态推进。"""
    if order.status not in ("approved", "partially_received"):
        raise BusinessError(f"只有已审核的采购单才能收货，当前状态: {order.status}")

    items = data.get("items") or []
    if not items:
        raise BusinessError("收货明细不能为空")
    # 数量校验：不得超过未收货数量；单价校验：不得为负
    item_map = {it.product_id: it for it in order.items}
    for it in items:
        qty = Decimal(it["qty"])
        if qty <= 0:
            raise BusinessError("收货数量必须大于0")
        price = Decimal(it.get("price", 0))
        if price < 0:
            raise BusinessError("收货单价不能为负")
        po_item = item_map.get(it["product_id"])
        if po_item is None:
            raise BusinessError(f"商品 #{it['product_id']} 不在采购单中")
        remain = po_item.qty - po_item.received_qty
        if qty > remain:
            raise BusinessError(f"商品「{po_item.product.name}」收货数量 {qty} 超过未收数量 {remain}")

    stock_in = StockIn(
        stock_in_no=gen_bill_no(db, "stock_in"),
        po_id=order.id,
        po_no=order.order_no,
        supplier_id=order.supplier_id,
        warehouse_id=order.warehouse_id,
        remark=data.get("remark"),
        created_by=username,
    )
    total = Decimal(0)
    for it in items:
        qty = Decimal(it["qty"])
        po_item = item_map[it["product_id"]]
        price = Decimal(it["price"])  # 按实际收货单价入账（前端默认带采购单价）
        amount = qty * price
        total += amount
        po_item.received_qty += qty
        stock_in.items.append(
            StockInItem(product_id=it["product_id"], qty=qty, price=price, amount=amount)
        )
        # 核心：库存变更 + 流水（原子）
        change_stock(
            db,
            product_id=it["product_id"],
            warehouse_id=order.warehouse_id,
            delta=qty,
            log_type="purchase_in",
            ref_no=stock_in.stock_in_no,
            created_by=username,
            remark=f"采购入库 {order.order_no}",
        )
    stock_in.total_amount = total
    db.add(stock_in)
    db.flush()

    # 挂应付（按实际收货金额）
    db.add(
        Payable(
            payable_no=gen_bill_no(db, "payable"),
            source_no=stock_in.stock_in_no,
            supplier_id=order.supplier_id,
            total_amount=total,
            due_date=date.today(),
            remark=f"采购入库 {order.order_no}",
            created_by=username,
        )
    )

    # 状态推进：全部收完 -> completed，否则 partially_received
    if all(
        item.received_qty >= item.qty for item in order.items
    ):
        order.status = "completed"
    else:
        order.status = "partially_received"
    return stock_in