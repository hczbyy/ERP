"""基础数据接口：商品分类、商品、客户、供应商、仓库。"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..deps import require_permission
from ..models import Customer, Product, ProductCategory, Supplier, Warehouse
from ..utils import BusinessError, fail, ok
from ..utils.pagination import paginate

router = APIRouter(prefix="/api/master", tags=["基础数据"])

# ---------- 商品分类 ----------


class CategoryBody(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    sort: int = 0


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _: object = Depends(require_permission("master:product:read"))):
    cats = db.query(ProductCategory).order_by(ProductCategory.sort, ProductCategory.id).all()
    return ok([{"id": c.id, "name": c.name, "sort": c.sort} for c in cats])


@router.post("/categories")
def create_category(
    body: CategoryBody,
    request: Request,
    db: Session = Depends(get_db),
    op=Depends(require_permission("master:product:manage")),
):
    if db.query(ProductCategory).filter(ProductCategory.name == body.name).first():
        return fail(f"分类 {body.name} 已存在")
    c = ProductCategory(**body.model_dump())
    db.add(c)
    db.flush()
    write_audit(db, op.username, "create", "master", target=f"分类 {body.name}", ip=request.client.host)
    db.commit()
    return ok({"id": c.id}, "分类创建成功")


@router.put("/categories/{cat_id}")
def update_category(
    cat_id: int, body: CategoryBody,
    request: Request, db: Session = Depends(get_db),
    op=Depends(require_permission("master:product:manage")),
):
    c = db.get(ProductCategory, cat_id)
    if not c:
        return fail("分类不存在")
    c.name, c.sort = body.name, body.sort
    write_audit(db, op.username, "update", "master", target=f"分类 {body.name}", ip=request.client.host)
    db.commit()
    return ok(message="分类更新成功")


@router.delete("/categories/{cat_id}")
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    op=Depends(require_permission("master:product:manage")),
):
    c = db.get(ProductCategory, cat_id)
    if not c:
        return fail("分类不存在")
    if db.query(Product).filter(Product.category_id == cat_id).first():
        return fail("该分类下存在商品，无法删除")
    db.delete(c)
    db.commit()
    return ok(message="分类已删除")


# ---------- 商品 ----------


class ProductBody(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    spec: str | None = None
    unit: str = "件"
    barcode: str | None = None
    category_id: int | None = None
    purchase_price: float = 0
    sale_price: float = 0
    safety_stock: float = 0
    status: str = "active"
    description: str | None = None


def _product_row(p: Product) -> dict:
    return {
        "id": p.id, "code": p.code, "name": p.name, "spec": p.spec,
        "unit": p.unit, "barcode": p.barcode, "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "purchase_price": float(p.purchase_price), "sale_price": float(p.sale_price),
        "safety_stock": float(p.safety_stock), "status": p.status,
        "description": p.description,
    }


@router.get("/products")
def list_products(
    keyword: str = "", category_id: int | None = None, page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("master:product:read")),
):
    q = db.query(Product)
    if keyword:
        q = q.filter(or_(Product.name.like(f"%{keyword}%"), Product.code.like(f"%{keyword}%")))
    if category_id:
        q = q.filter(Product.category_id == category_id)
    result = paginate(db, q.order_by(Product.id.desc()), page, page_size)
    result["items"] = [_product_row(p) for p in result["items"]]
    return ok(result)


@router.get("/products/all")
def all_products(
    status: str = "active",
    db: Session = Depends(get_db), _=Depends(require_permission("master:product:read")),
):
    """下拉选择用：返回全量（含当前库存，前端做库存校验提示）。"""
    q = db.query(Product)
    if status:
        q = q.filter(Product.status == status)
    return ok([_product_row(p) for p in q.order_by(Product.id).all()])


@router.post("/products")
def create_product(
    body: ProductBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:product:manage")),
):
    if db.query(Product).filter(Product.code == body.code).first():
        return fail(f"商品编码 {body.code} 已存在")
    p = Product(**body.model_dump())
    db.add(p)
    db.flush()
    write_audit(db, op.username, "create", "master", target=f"商品 {body.name}", ip=request.client.host)
    db.commit()
    return ok({"id": p.id}, "商品创建成功")


@router.put("/products/{product_id}")
def update_product(
    product_id: int, body: ProductBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:product:manage")),
):
    p = db.get(Product, product_id)
    if not p:
        return fail("商品不存在")
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    write_audit(db, op.username, "update", "master", target=f"商品 {body.name}", ip=request.client.host)
    db.commit()
    return ok(message="商品更新成功")


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:product:manage")),
):
    p = db.get(Product, product_id)
    if not p:
        return fail("商品不存在")
    from ..models import PurchaseOrderItem, SalesOrderItem, Stock
    if (
        db.query(PurchaseOrderItem).filter_by(product_id=product_id).first()
        or db.query(SalesOrderItem).filter_by(product_id=product_id).first()
        or db.query(Stock).filter_by(product_id=product_id).first()
    ):
        return fail("商品已发生业务单据或存在库存，请改为停用")
    db.delete(p)
    write_audit(db, op.username, "delete", "master", target=f"商品 {p.name}", ip=request.client.host)
    db.commit()
    return ok(message="商品已删除")


# ---------- 客户 ----------


class CustomerBody(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    contact: str | None = None
    phone: str | None = None
    address: str | None = None
    credit_limit: float = 0
    status: str = "active"


def _customer_row(c: Customer) -> dict:
    return {
        "id": c.id, "code": c.code, "name": c.name, "contact": c.contact,
        "phone": c.phone, "address": c.address, "credit_limit": float(c.credit_limit),
        "status": c.status,
    }


@router.get("/customers")
def list_customers(
    keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("master:customer:read")),
):
    q = db.query(Customer)
    if keyword:
        q = q.filter(or_(Customer.name.like(f"%{keyword}%"), Customer.code.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(Customer.id.desc()), page, page_size)
    result["items"] = [_customer_row(c) for c in result["items"]]
    return ok(result)


@router.get("/customers/all")
def all_customers(
    status: str = "active",
    db: Session = Depends(get_db), _=Depends(require_permission("master:customer:read")),
):
    q = db.query(Customer)
    if status:
        q = q.filter(Customer.status == status)
    return ok([_customer_row(c) for c in q.order_by(Customer.id).all()])


@router.post("/customers")
def create_customer(
    body: CustomerBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:customer:manage")),
):
    if db.query(Customer).filter(Customer.code == body.code).first():
        return fail(f"客户编码 {body.code} 已存在")
    c = Customer(**body.model_dump())
    db.add(c)
    db.flush()
    write_audit(db, op.username, "create", "master", target=f"客户 {body.name}", ip=request.client.host)
    db.commit()
    return ok({"id": c.id}, "客户创建成功")


@router.put("/customers/{cust_id}")
def update_customer(
    cust_id: int, body: CustomerBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:customer:manage")),
):
    c = db.get(Customer, cust_id)
    if not c:
        return fail("客户不存在")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    write_audit(db, op.username, "update", "master", target=f"客户 {body.name}", ip=request.client.host)
    db.commit()
    return ok(message="客户更新成功")


@router.delete("/customers/{cust_id}")
def delete_customer(
    cust_id: int,
    db: Session = Depends(get_db), op=Depends(require_permission("master:customer:manage")),
):
    c = db.get(Customer, cust_id)
    if not c:
        return fail("客户不存在")
    from ..models import SalesOrder
    if db.query(SalesOrder).filter_by(customer_id=cust_id).first():
        return fail("该客户存在销售单据，请改为停用")
    db.delete(c)
    db.commit()
    return ok(message="客户已删除")


# ---------- 供应商 ----------


class SupplierBody(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    contact: str | None = None
    phone: str | None = None
    address: str | None = None
    status: str = "active"


def _supplier_row(s: Supplier) -> dict:
    return {
        "id": s.id, "code": s.code, "name": s.name, "contact": s.contact,
        "phone": s.phone, "address": s.address, "status": s.status,
    }


@router.get("/suppliers")
def list_suppliers(
    keyword: str = "", page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), _=Depends(require_permission("master:supplier:read")),
):
    q = db.query(Supplier)
    if keyword:
        q = q.filter(or_(Supplier.name.like(f"%{keyword}%"), Supplier.code.like(f"%{keyword}%")))
    result = paginate(db, q.order_by(Supplier.id.desc()), page, page_size)
    result["items"] = [_supplier_row(s) for s in result["items"]]
    return ok(result)


@router.get("/suppliers/all")
def all_suppliers(
    status: str = "active",
    db: Session = Depends(get_db), _=Depends(require_permission("master:supplier:read")),
):
    q = db.query(Supplier)
    if status:
        q = q.filter(Supplier.status == status)
    return ok([_supplier_row(s) for s in q.order_by(Supplier.id).all()])


@router.post("/suppliers")
def create_supplier(
    body: SupplierBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:supplier:manage")),
):
    if db.query(Supplier).filter(Supplier.code == body.code).first():
        return fail(f"供应商编码 {body.code} 已存在")
    s = Supplier(**body.model_dump())
    db.add(s)
    db.flush()
    write_audit(db, op.username, "create", "master", target=f"供应商 {body.name}", ip=request.client.host)
    db.commit()
    return ok({"id": s.id}, "供应商创建成功")


@router.put("/suppliers/{sup_id}")
def update_supplier(
    sup_id: int, body: SupplierBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:supplier:manage")),
):
    s = db.get(Supplier, sup_id)
    if not s:
        return fail("供应商不存在")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    write_audit(db, op.username, "update", "master", target=f"供应商 {body.name}", ip=request.client.host)
    db.commit()
    return ok(message="供应商更新成功")


@router.delete("/suppliers/{sup_id}")
def delete_supplier(
    sup_id: int,
    db: Session = Depends(get_db), op=Depends(require_permission("master:supplier:manage")),
):
    s = db.get(Supplier, sup_id)
    if not s:
        return fail("供应商不存在")
    from ..models import PurchaseOrder
    if db.query(PurchaseOrder).filter_by(supplier_id=sup_id).first():
        return fail("该供应商存在采购单据，请改为停用")
    db.delete(s)
    db.commit()
    return ok(message="供应商已删除")


# ---------- 仓库 ----------


class WarehouseBody(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    address: str | None = None
    manager: str | None = None
    status: str = "active"


def _warehouse_row(w: Warehouse) -> dict:
    return {
        "id": w.id, "code": w.code, "name": w.name, "address": w.address,
        "manager": w.manager, "status": w.status,
    }


@router.get("/warehouses")
def list_warehouses(
    db: Session = Depends(get_db), _=Depends(require_permission("master:warehouse:read")),
):
    return ok([_warehouse_row(w) for w in db.query(Warehouse).order_by(Warehouse.id).all()])


@router.post("/warehouses")
def create_warehouse(
    body: WarehouseBody, request: Request,
    db: Session = Depends(get_db), op=Depends(require_permission("master:warehouse:manage")),
):
    if db.query(Warehouse).filter(Warehouse.code == body.code).first():
        return fail(f"仓库编码 {body.code} 已存在")
    w = Warehouse(**body.model_dump())
    db.add(w)
    db.flush()
    write_audit(db, op.username, "create", "master", target=f"仓库 {body.name}", ip=request.client.host)
    db.commit()
    return ok({"id": w.id}, "仓库创建成功")


@router.put("/warehouses/{wh_id}")
def update_warehouse(
    wh_id: int, body: WarehouseBody,
    db: Session = Depends(get_db), op=Depends(require_permission("master:warehouse:manage")),
):
    w = db.get(Warehouse, wh_id)
    if not w:
        return fail("仓库不存在")
    for k, v in body.model_dump().items():
        setattr(w, k, v)
    write_audit(db, op.username, "update", "master", target=f"仓库 {body.name}")
    db.commit()
    return ok(message="仓库更新成功")


@router.delete("/warehouses/{wh_id}")
def delete_warehouse(
    wh_id: int,
    db: Session = Depends(get_db), op=Depends(require_permission("master:warehouse:manage")),
):
    w = db.get(Warehouse, wh_id)
    if not w:
        return fail("仓库不存在")
    from ..models import Stock
    if db.query(Stock).filter_by(warehouse_id=wh_id).first():
        return fail("该仓库存在库存记录，无法删除")
    db.delete(w)
    db.commit()
    return ok(message="仓库已删除")