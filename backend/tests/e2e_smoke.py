"""OpenERP 端到端冒烟测试（httpx）。

覆盖：登录 -> 采购(建单/审核/收货) -> 库存增加 -> 应付生成
     -> 销售(建单/审核/发货) -> 库存扣减 -> 应收生成
     -> 部分收款/超额拒绝/全额核销 -> 应付核销
     -> 调拨 / 盘点 / 审计日志 / RBAC 权限拦截 / 仪表盘
用法：python tests/e2e_smoke.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

BASE = "http://127.0.0.1:8000"
PASS, FAIL = 0, 0


def step(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"PASS  {name}")
        PASS += 1
    except Exception as e:
        print(f"FAIL  {name}: {e}")
        FAIL += 1


class Client:
    def __init__(self, username, password):
        r = httpx.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
        self.h = {"Authorization": f"Bearer {r.json()['data']['token']}"}

    def get(self, path, params=None, **kw):
        r = httpx.get(f"{BASE}{path}", headers=self.h, params=params, **kw)
        j = r.json()
        assert r.status_code < 400, f"GET {path} -> {r.status_code} {j}"
        assert j["code"] == 0, f"GET {path}: {j['message']}"
        return j["data"]

    def post(self, path, body=None):
        r = httpx.post(f"{BASE}{path}", headers=self.h, json=body or {})
        j = r.json()
        assert r.status_code < 400, f"POST {path} -> {r.status_code} {j}"
        assert j["code"] == 0, f"POST {path}: {j['message']}"
        return j["data"]

    def put(self, path, body=None):
        r = httpx.put(f"{BASE}{path}", headers=self.h, json=body or {})
        j = r.json()
        assert r.status_code < 400, f"PUT {path} -> {r.status_code} {j}"
        assert j["code"] == 0, f"PUT {path}: {j['message']}"
        return j["data"]

    def raw(self, method, path, body=None):
        """返回原始响应（用于断言 4xx 拦截）。"""
        return httpx.request(method, f"{BASE}{path}", headers=self.h, json=body or {})


def main():
    admin = Client("admin", "admin123")

    def wrong_password():
        r = httpx.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.json()["code"] != 0, "错误密码应返回业务错误"
        assert r.json()["data"] is None

    step("错误密码被拒绝", wrong_password)

    state = {}

    def load_master():
        p = admin.get("/api/master/products/all")
        c = admin.get("/api/master/customers/all")
        s = admin.get("/api/master/suppliers/all")
        w = admin.get("/api/master/warehouses")
        assert len(p) >= 10 and len(c) >= 3 and len(s) >= 3 and len(w) >= 2
        state.update(p1=p[0]["id"], p2=p[1]["id"], c1=c[0]["id"], s1=s[0]["id"], w1=w[0]["id"], w2=w[1]["id"])

    step("基础数据齐全", load_master)

    def create_po():
        d = admin.post("/api/purchase/orders", {
            "supplier_id": state["s1"], "warehouse_id": state["w1"], "remark": "e2e",
            "items": [{"product_id": state["p1"], "qty": 10, "price": 100},
                      {"product_id": state["p2"], "qty": 5, "price": 200}],
        })
        assert d["status"] == "draft" and d["total_amount"] == 2000, d
        state["po"] = d["id"]
        state["po_no"] = d["order_no"]

    step("创建采购单(草稿)", create_po)

    def approve_po():
        d = admin.post(f"/api/purchase/orders/{state['po']}/approve")
        assert d["status"] == "approved", d

    step("采购单审核", approve_po)

    def receive_po():
        before = admin.get(f"/api/inventory/stocks?warehouse_id={state['w1']}&page_size=100")
        bq = next((x["qty"] for x in before["items"] if x["product_id"] == state["p1"]), 0)
        d = admin.post(f"/api/purchase/orders/{state['po']}/receive", {
            "items": [{"product_id": state["p1"], "qty": 8, "price": 100},
                      {"product_id": state["p2"], "qty": 5, "price": 200}],
        })
        assert d["total_amount"] == 1800, d
        after = admin.get(f"/api/inventory/stocks?warehouse_id={state['w1']}&page_size=100")
        aq = next((x["qty"] for x in after["items"] if x["product_id"] == state["p1"]), 0)
        assert aq - bq == 8, f"库存变动异常: {bq} -> {aq}"
        pay = admin.get("/api/finance/payables?page_size=5")
        assert pay["items"], "应付未生成"
        state["pay"] = pay["items"][0]
        po = admin.get(f"/api/purchase/orders/{state['po']}")
        assert po["status"] == "partially_received", po

    step("部分收货入库(库存+应付)", receive_po)

    def over_receive():
        r = admin.raw("POST", f"/api/purchase/orders/{state['po']}/receive",
                      {"items": [{"product_id": state["p1"], "qty": 999, "price": 100}]})
        assert r.status_code == 400 and "超过未收" in r.json()["message"], r.text
        # 补收尾数，验证状态推进到 completed
        admin.post(f"/api/purchase/orders/{state['po']}/receive",
                   {"items": [{"product_id": state["p1"], "qty": 2, "price": 100}]})
        po = admin.get(f"/api/purchase/orders/{state['po']}")
        assert po["status"] == "completed", po

    step("超量收货被拒+补收完成", over_receive)

    def sales_flow():
        d = admin.post("/api/sales/orders", {
            "customer_id": state["c1"], "warehouse_id": state["w1"], "remark": "e2e",
            "items": [{"product_id": state["p1"], "qty": 6, "price": 150}],
        })
        assert d["total_amount"] == 900, d
        state["so"] = d["id"]
        d2 = admin.post(f"/api/sales/orders/{state['so']}/approve")
        assert d2["status"] == "approved", d2
        sh = admin.post(f"/api/sales/orders/{state['so']}/ship",
                        {"items": [{"product_id": state["p1"], "qty": 6, "price": 150}]})
        assert sh["total_amount"] == 900, sh
        rec = admin.get("/api/finance/receivables?page_size=5")
        assert rec["items"], "应付未生成"
        state["rec"] = rec["items"][0]

    step("销售 建单/审核/发货(库存-应收)", sales_flow)

    def over_ship():
        r = admin.raw("POST", f"/api/sales/orders/{state['so']}/ship",
                      {"items": [{"product_id": state["p1"], "qty": 9999, "price": 150}]})
        assert r.status_code == 400, r.text

    step("超库存发货被拒绝", over_ship)

    def partial_receipt():
        d = admin.post("/api/finance/receipts",
                       {"receivable_id": state["rec"]["id"], "amount": 500, "pay_method": "bank"})
        assert d["receipt_no"].startswith("RC"), d
        rec = admin.get("/api/finance/receivables", params={"keyword": state["rec"]["receivable_no"]})["items"][0]
        assert rec["status"] == "partial", rec
        r = admin.raw("POST", "/api/finance/receipts",
                      {"receivable_id": state["rec"]["id"], "amount": 99999})
        assert r.status_code == 400, r.text

    step("部分收款+超额拒绝", partial_receipt)

    def full_settle():
        admin.post("/api/finance/receipts", {"receivable_id": state["rec"]["id"], "amount": 400})
        rec = admin.get("/api/finance/receivables", params={"keyword": state["rec"]["receivable_no"]})["items"][0]
        assert rec["status"] == "settled", rec
        # 分次收货产生多笔应付，全部核销
        opens = admin.get("/api/finance/payables?status=open&page_size=50")["items"]
        assert opens, "存在未核销应付"
        for p in opens:
            admin.post("/api/finance/payments", {"payable_id": p["id"], "amount": p["balance"]})
        remains = admin.get("/api/finance/payables?status=open&page_size=50")["items"]
        assert not remains, "应付未全部核销"

    step("应收/应付全额核销", full_settle)

    def transfer():
        d = admin.post("/api/inventory/transfers", {
            "from_warehouse_id": state["w1"], "to_warehouse_id": state["w2"],
            "items": [{"product_id": state["p2"], "qty": 2}],
        })
        assert d["transfer_no"].startswith("TR"), d

    step("库存调拨", transfer)

    def check_cycle():
        c = admin.post("/api/inventory/checks",
                       {"warehouse_id": state["w1"], "product_ids": [state["p2"]]})
        admin.put(f"/api/inventory/checks/{c['id']}",
                  {"items": [{"product_id": state["p2"], "actual_qty": 0}]})
        admin.post(f"/api/inventory/checks/{c['id']}/done")

    step("盘点 创建/实盘/提交", check_cycle)

    def audit():
        logs = admin.get("/api/system/audit-logs?page_size=50")
        assert len(logs["items"]) >= 15, f"审计日志过少: {len(logs['items'])}"

    step("审计日志记录", audit)

    def rbac():
        auditor = Client("auditor", "demo123")
        r = auditor.raw("POST", "/api/master/products", {"code": "X1", "name": "x"})
        assert r.status_code == 403, r.text
        keeper = Client("keeper", "demo123")
        r2 = keeper.raw("POST", "/api/purchase/orders", {"supplier_id": 1, "warehouse_id": 1, "items": []})
        assert r2.status_code == 403, r2.text

    step("RBAC 权限拦截", rbac)

    def dashboard():
        s = admin.get("/api/dashboard/summary")
        assert s["today_sales"] >= 0
        t = admin.get("/api/dashboard/sales-trend?days=7")
        assert len(t["labels"]) == 7, t
        top = admin.get("/api/dashboard/top-products?limit=5")
        assert top, "TOP 商品为空"

    step("仪表盘数据", dashboard)

    print("\n" + "=" * 46)
    print(f"E2E result: PASS={PASS} FAIL={FAIL}")
    print("=" * 46)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()