"""基础数据模块 API：分类 / 商品 / 客户 / 供应商 / 仓库 的增删改查。"""
from api.base import BaseApi


class MasterApi(BaseApi):
    # ---------- 分类 ----------

    def list_categories(self, **params):
        """GET /api/master/categories"""
        return self._get("/api/master/categories", params=params or None)

    def create_category(self, body: dict):
        """POST /api/master/categories"""
        return self._post("/api/master/categories", json=body)

    def update_category(self, cat_id: int, body: dict):
        """PUT /api/master/categories/{cat_id}"""
        return self._put(f"/api/master/categories/{cat_id}", json=body)

    def delete_category(self, cat_id: int):
        """DELETE /api/master/categories/{cat_id}"""
        return self._delete(f"/api/master/categories/{cat_id}")

    # ---------- 商品 ----------

    def list_products(self, **params):
        """GET /api/master/products（keyword/category_id/page/page_size）"""
        return self._get("/api/master/products", params=params or None)

    def create_product(self, body: dict):
        """POST /api/master/products"""
        return self._post("/api/master/products", json=body)

    def all_products(self, status: str | None = None):
        """GET /api/master/products/all（下拉全量）"""
        return self._get("/api/master/products/all", params={"status": status} if status else None)

    def update_product(self, product_id: int, body: dict):
        """PUT /api/master/products/{product_id}"""
        return self._put(f"/api/master/products/{product_id}", json=body)

    def delete_product(self, product_id: int):
        """DELETE /api/master/products/{product_id}"""
        return self._delete(f"/api/master/products/{product_id}")

    # ---------- 客户 ----------

    def list_customers(self, **params):
        """GET /api/master/customers"""
        return self._get("/api/master/customers", params=params or None)

    def create_customer(self, body: dict):
        """POST /api/master/customers"""
        return self._post("/api/master/customers", json=body)

    def all_customers(self, status: str | None = None):
        """GET /api/master/customers/all"""
        return self._get("/api/master/customers/all", params={"status": status} if status else None)

    def update_customer(self, cust_id: int, body: dict):
        """PUT /api/master/customers/{cust_id}"""
        return self._put(f"/api/master/customers/{cust_id}", json=body)

    def delete_customer(self, cust_id: int):
        """DELETE /api/master/customers/{cust_id}"""
        return self._delete(f"/api/master/customers/{cust_id}")

    # ---------- 供应商 ----------

    def list_suppliers(self, **params):
        """GET /api/master/suppliers"""
        return self._get("/api/master/suppliers", params=params or None)

    def create_supplier(self, body: dict):
        """POST /api/master/suppliers"""
        return self._post("/api/master/suppliers", json=body)

    def all_suppliers(self, status: str | None = None):
        """GET /api/master/suppliers/all"""
        return self._get("/api/master/suppliers/all", params={"status": status} if status else None)

    def update_supplier(self, sup_id: int, body: dict):
        """PUT /api/master/suppliers/{sup_id}"""
        return self._put(f"/api/master/suppliers/{sup_id}", json=body)

    def delete_supplier(self, sup_id: int):
        """DELETE /api/master/suppliers/{sup_id}"""
        return self._delete(f"/api/master/suppliers/{sup_id}")

    # ---------- 仓库 ----------

    def list_warehouses(self, **params):
        """GET /api/master/warehouses"""
        return self._get("/api/master/warehouses", params=params or None)

    def create_warehouse(self, body: dict):
        """POST /api/master/warehouses"""
        return self._post("/api/master/warehouses", json=body)

    def update_warehouse(self, wh_id: int, body: dict):
        """PUT /api/master/warehouses/{wh_id}"""
        return self._put(f"/api/master/warehouses/{wh_id}", json=body)

    def delete_warehouse(self, wh_id: int):
        """DELETE /api/master/warehouses/{wh_id}"""
        return self._delete(f"/api/master/warehouses/{wh_id}")