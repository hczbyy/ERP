"""销售管理模块 API：销售订单全生命周期（创建/审核/取消/发货）+ 出库单。"""
from api.base import BaseApi


class SalesApi(BaseApi):
    # ---------- 销售订单 ----------

    def list_orders(self, **params):
        """GET /api/sales/orders（status/keyword/page/page_size）"""
        return self._get("/api/sales/orders", params=params or None)

    def create_order(self, body: dict):
        """POST /api/sales/orders"""
        return self._post("/api/sales/orders", json=body)

    def order_detail(self, order_id: int):
        """GET /api/sales/orders/{order_id}"""
        return self._get(f"/api/sales/orders/{order_id}")

    def update_order(self, order_id: int, body: dict):
        """PUT /api/sales/orders/{order_id}"""
        return self._put(f"/api/sales/orders/{order_id}", json=body)

    def delete_order(self, order_id: int):
        """DELETE /api/sales/orders/{order_id}"""
        return self._delete(f"/api/sales/orders/{order_id}")

    def approve_order(self, order_id: int):
        """POST /api/sales/orders/{order_id}/approve（审核）"""
        return self._post(f"/api/sales/orders/{order_id}/approve")

    def cancel_order(self, order_id: int, body: dict | None = None):
        """POST /api/sales/orders/{order_id}/cancel（取消，body 可带 reason）"""
        return self._post(f"/api/sales/orders/{order_id}/cancel", json=body or {})

    def ship_order(self, order_id: int, body: dict):
        """POST /api/sales/orders/{order_id}/ship（发货出库：库存扣减 + 应收挂账）"""
        return self._post(f"/api/sales/orders/{order_id}/ship", json=body)

    # ---------- 出库单 ----------

    def list_stock_outs(self, **params):
        """GET /api/sales/stock-outs"""
        return self._get("/api/sales/stock-outs", params=params or None)

    def stock_out_detail(self, so_id: int):
        """GET /api/sales/stock-outs/{so_id}"""
        return self._get(f"/api/sales/stock-outs/{so_id}")