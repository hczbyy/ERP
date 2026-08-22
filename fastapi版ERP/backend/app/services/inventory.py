"""库存服务：所有库存变动必须经过 change_stock，保证 Stock 与 StockLog 强一致。

change_stock 不自行提交事务，由调用方（订单服务/API）统一 commit，
确保「库存 + 流水 + 业务单据」原子生效。
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import Stock, StockLog
from ..utils import BusinessError


def change_stock(
    db: Session,
    *,
    product_id: int,
    warehouse_id: int,
    delta: Decimal,
    log_type: str,
    ref_no: str | None,
    created_by: str,
    remark: str | None = None,
) -> Stock:
    """变更库存并写流水。delta > 0 入库，delta < 0 出库。

    出库时校验库存充足，防止负库存。
    """
    delta = Decimal(delta)
    stock = (
        db.query(Stock)
        .filter_by(product_id=product_id, warehouse_id=warehouse_id)
        .first()
    )
    if stock is None:
        if delta < 0:
            raise BusinessError("该商品在此仓库没有库存，无法出库")
        stock = Stock(product_id=product_id, warehouse_id=warehouse_id, qty=Decimal(0))
        db.add(stock)
        db.flush()

    before = stock.qty
    after = before + delta
    if after < 0:
        raise BusinessError(f"库存不足：商品#{product_id} 当前 {before}，本次需要 {abs(delta)}")

    stock.qty = after
    db.add(
        StockLog(
            product_id=product_id,
            warehouse_id=warehouse_id,
            change_qty=delta,
            before_qty=before,
            after_qty=after,
            log_type=log_type,
            ref_no=ref_no,
            remark=remark,
            created_by=created_by,
        )
    )
    return stock


def get_stock_qty(db: Session, product_id: int, warehouse_id: int) -> Decimal:
    stock = (
        db.query(Stock)
        .filter_by(product_id=product_id, warehouse_id=warehouse_id)
        .first()
    )
    return stock.qty if stock else Decimal(0)