"""库存管理模块 API：库存查询 / 流水 / 盘点 / 调拨。"""
from api.base import BaseApi


class InventoryApi(BaseApi):
    # ---------- 库存 ----------

    def list_stocks(self, **params):
        """GET /api/inventory/stocks（keyword/warehouse_id/low_stock_only/page/page_size）"""
        return self._get("/api/inventory/stocks", params=params or None)

    def list_logs(self, **params):
        """GET /api/inventory/logs（product_id/warehouse_id/log_type/page/page_size）"""
        return self._get("/api/inventory/logs", params=params or None)

    # ---------- 盘点 ----------

    def list_checks(self, **params):
        """GET /api/inventory/checks（status/page/page_size）"""
        return self._get("/api/inventory/checks", params=params or None)

    def create_check(self, body: dict):
        """POST /api/inventory/checks"""
        return self._post("/api/inventory/checks", json=body)

    def check_detail(self, check_id: int):
        """GET /api/inventory/checks/{check_id}"""
        return self._get(f"/api/inventory/checks/{check_id}")

    def update_check(self, check_id: int, body: dict):
        """PUT /api/inventory/checks/{check_id}"""
        return self._put(f"/api/inventory/checks/{check_id}", json=body)

    def done_check(self, check_id: int):
        """POST /api/inventory/checks/{check_id}/done（按差异调整库存）"""
        return self._post(f"/api/inventory/checks/{check_id}/done")

    # ---------- 调拨 ----------

    def list_transfers(self, **params):
        """GET /api/inventory/transfers"""
        return self._get("/api/inventory/transfers", params=params or None)

    def create_transfer(self, body: dict):
        """POST /api/inventory/transfers"""
        return self._post("/api/inventory/transfers", json=body)