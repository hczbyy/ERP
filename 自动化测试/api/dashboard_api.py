"""仪表盘模块 API：汇总 / 销售趋势 / TOP 商品 / 库存预警 / 最近订单 / 健康检查。"""
from api.base import BaseApi


class DashboardApi(BaseApi):
    def summary(self):
        """GET /api/dashboard/summary"""
        return self._get("/api/dashboard/summary")

    def sales_trend(self, days: int | None = None):
        """GET /api/dashboard/sales-trend"""
        return self._get("/api/dashboard/sales-trend", params={"days": days} if days else None)

    def top_products(self, limit: int | None = None):
        """GET /api/dashboard/top-products"""
        return self._get("/api/dashboard/top-products", params={"limit": limit} if limit else None)

    def low_stocks(self, limit: int | None = None):
        """GET /api/dashboard/low-stocks"""
        return self._get("/api/dashboard/low-stocks", params={"limit": limit} if limit else None)

    def recent_orders(self, limit: int | None = None):
        """GET /api/dashboard/recent-orders"""
        return self._get("/api/dashboard/recent-orders", params={"limit": limit} if limit else None)

    def health(self):
        """GET /api/health"""
        return self._get("/api/health", need_token=False)