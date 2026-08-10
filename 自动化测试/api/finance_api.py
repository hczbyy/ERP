"""财务管理模块 API：应收 / 应付 / 收款 / 付款。"""
from api.base import BaseApi


class FinanceApi(BaseApi):
    def list_receivables(self, **params):
        """GET /api/finance/receivables（status/keyword/page/page_size）"""
        return self._get("/api/finance/receivables", params=params or None)

    def list_payables(self, **params):
        """GET /api/finance/payables（status/keyword/page/page_size）"""
        return self._get("/api/finance/payables", params=params or None)

    def list_receipts(self, **params):
        """GET /api/finance/receipts"""
        return self._get("/api/finance/receipts", params=params or None)

    def create_receipt(self, body: dict):
        """POST /api/finance/receipts（收款核销应收）"""
        return self._post("/api/finance/receipts", json=body)

    def list_payments(self, **params):
        """GET /api/finance/payments"""
        return self._get("/api/finance/payments", params=params or None)

    def create_payment(self, body: dict):
        """POST /api/finance/payments（付款核销应付）"""
        return self._post("/api/finance/payments", json=body)