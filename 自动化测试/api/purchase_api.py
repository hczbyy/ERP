"""采购管理模块 API：采购订单全生命周期（创建/审核/取消/收货）+ 入库单。"""
from api.base import BaseApi


class PurchaseApi(BaseApi):
    # ---------- 采购订单 ----------

    def list_orders(self, **params):
        """GET /api/purchase/orders（status/keyword/page/page_size）"""
        return self._get("/api/purchase/orders", params=params or None)

    def create_order(self, body: dict):
        """POST /api/purchase/orders"""
        return self._post("/api/purchase/orders", json=body)

    def order_detail(self, order_id: int):
        """GET /api/purchase/orders/{order_id}"""
        return self._get(f"/api/purchase/orders/{order_id}")

    def update_order(self, order_id: int, body: dict):
        """PUT /api/purchase/orders/{order_id}"""
        return self._put(f"/api/purchase/orders/{order_id}", json=body)

    def delete_order(self, order_id: int):
        """DELETE /api/purchase/orders/{order_id}"""
        return self._delete(f"/api/purchase/orders/{order_id}")

    def approve_order(self, order_id: int):
        """POST /api/purchase/orders/{order_id}/approve（审核）"""
        return self._post(f"/api/purchase/orders/{order_id}/approve")

    def cancel_order(self, order_id: int, body: dict | None = None):
        """POST /api/purchase/orders/{order_id}/cancel（取消，body 可带 reason）"""
        return self._post(f"/api/purchase/orders/{order_id}/cancel", json=body or {})

    def receive_order(self, order_id: int, body: dict):
        """POST /api/purchase/orders/{order_id}/receive（收货入库：库存增加 + 应付挂账）"""
        return self._post(f"/api/purchase/orders/{order_id}/receive", json=body)

    # ---------- 入库单 ----------

    def list_stock_ins(self, **params):
        """GET /api/purchase/stock-ins"""
        return self._get("/api/purchase/stock-ins", params=params or None)

    def stock_in_detail(self, si_id: int):
        """GET /api/purchase/stock-ins/{si_id}"""
        return self._get(f"/api/purchase/stock-ins/{si_id}")