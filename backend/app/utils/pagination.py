"""分页辅助：统一列表响应结构。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Query, Session


def paginate(db: Session, query: Query, page: int = 1, page_size: int = 20) -> dict:
    """对任意 Query 分页，返回统一结构。page 从 1 开始。"""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}