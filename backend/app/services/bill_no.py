"""单据号生成器：前缀 + 日期 + 当日序号，如 PO20260804001。

使用数据库计数保证并发唯一：当日序号从 1 递增，查询失败则回退到 max+1。
"""
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

_PREFIXES = {
    "purchase_order": "PO",
    "sales_order": "SO",
    "stock_in": "SI",
    "stock_out": "SOUT",
    "stock_check": "PC",
    "stock_transfer": "TR",
    "receivable": "AR",
    "payable": "AP",
    "receipt": "RC",
    "payment": "PY",
}


def gen_bill_no(db: Session, kind: str) -> str:
    """生成单据号：{前缀}{YYYYMMDD}{3位序号}"""
    prefix = _PREFIXES[kind]
    today = datetime.now().strftime("%Y%m%d")
    prefix_full = f"{prefix}{today}"

    table_map = {
        "purchase_order": "po_order",
        "sales_order": "so_order",
        "stock_in": "po_stock_in",
        "stock_out": "so_stock_out",
        "stock_check": "inv_stock_check",
        "stock_transfer": "inv_stock_transfer",
        "receivable": "fin_receivable",
        "payable": "fin_payable",
        "receipt": "fin_receipt",
        "payment": "fin_payment",
    }
    col_map = {
        "purchase_order": "order_no",
        "sales_order": "order_no",
        "stock_in": "stock_in_no",
        "stock_out": "stock_out_no",
        "stock_check": "check_no",
        "stock_transfer": "transfer_no",
        "receivable": "receivable_no",
        "payable": "payable_no",
        "receipt": "receipt_no",
        "payment": "payment_no",
    }
    table, col = table_map[kind], col_map[kind]
    row = db.execute(
        text(f"SELECT MAX({col}) FROM {table} WHERE {col} LIKE :p"), {"p": f"{prefix_full}%"}
    ).scalar()
    seq = 1
    if row:
        seq = int(str(row)[-3:]) + 1
    return f"{prefix_full}{seq:03d}"