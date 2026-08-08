"""OpenERP 接口自动化测试（pytest + TestClient，独立临时数据库）。

设计：模块级 fixture flow_state 在内部执行完整业务链
（采购建单/审核/收货 -> 销售建单/审核/发货 -> 收付款核销 -> 调拨/盘点），
各测试类只对结果做断言，测试之间无顺序依赖。
"""
import pytest


# ================= 模块级业务链 fixture =================

@pytest.fixture(scope="module")
def flow_state(admin, api):
    """执行完整业务链，返回各环节关键结果供断言。"""
    st = {}
    p = admin.get("/api/master/products/all")
    c = admin.get("/api/master/customers/all")
    s = admin.get("/api/master/suppliers/all")
    w = admin.get("/api/master/warehouses")
    assert len(p) >= 10 and len(c) >= 3 and len(s) >= 3 and len(w) >= 2
    st.update(p1=p[0]["id"], p2=p[1]["id"], c1=c[0]["id"], s1=s[0]["id"], w1=w[0]["id"], w2=w[1]["id"])

    # ---- 采购：建单(草稿) -> 审核 -> 部分收货 -> 超量被拒 -> 补收完成 ----
    po = admin.post("/api/purchase/orders", {
        "supplier_id": st["s1"], "warehouse_id": st["w1"], "remark": "pytest",
        "items": [{"product_id": st["p1"], "qty": 10, "price": 100},
                  {"product_id": st["p2"], "qty": 5, "price": 200}],
    })
    assert po["status"] == "draft" and po["total_amount"] == 2000
    assert "%" not in po["order_no"], "单号不应包含 %"
    st["po"] = po
    st["po_id"] = po["id"]
    st["po_no"] = po["order_no"]

    assert admin.post(f"/api/purchase/orders/{po['id']}/approve")["status"] == "approved"

    before = admin.get("/api/inventory/stocks", warehouse_id=st["w1"], page_size=100)
    st["stock_p1_before"] = next(x["qty"] for x in before["items"] if x["product_id"] == st["p1"])

    si = admin.post(f"/api/purchase/orders/{po['id']}/receive", {
        "items": [{"product_id": st["p1"], "qty": 8, "price": 100},
                  {"product_id": st["p2"], "qty": 5, "price": 200}],
    })
    assert si["total_amount"] == 1800
    st["stock_in"] = si

    after = admin.get("/api/inventory/stocks", warehouse_id=st["w1"], page_size=100)
    st["stock_p1_after"] = next(x["qty"] for x in after["items"] if x["product_id"] == st["p1"])

    po_after = admin.get(f"/api/purchase/orders/{po['id']}")
    assert po_after["status"] == "partially_received"

    pay = admin.get("/api/finance/payables", page_size=5)
    st["payable"] = pay["items"][0]
    assert st["payable"]["total_amount"] == 1800

    over = api("admin", "admin123").raw(
        "POST", f"/api/purchase/orders/{po['id']}/receive",
        {"items": [{"product_id": st["p1"], "qty": 999, "price": 100}]})
    st["over_receive_code"] = over.status_code
    st["over_receive_msg"] = over.json()["message"]

    admin.post(f"/api/purchase/orders/{po['id']}/receive",
               {"items": [{"product_id": st["p1"], "qty": 2, "price": 100}]})
    st["po_final_status"] = admin.get(f"/api/purchase/orders/{po['id']}")["status"]

    # ---- 销售：建单 -> 审核 -> 发货 -> 应收 ----
    so = admin.post("/api/sales/orders", {
        "customer_id": st["c1"], "warehouse_id": st["w1"], "remark": "pytest",
        "items": [{"product_id": st["p1"], "qty": 6, "price": 150}],
    })
    assert so["total_amount"] == 900
    assert admin.post(f"/api/sales/orders/{so['id']}/approve")["status"] == "approved"
    sh = admin.post(f"/api/sales/orders/{so['id']}/ship",
                    {"items": [{"product_id": st["p1"], "qty": 6, "price": 150}]})
    assert sh["total_amount"] == 900
    st["so"] = so
    st["ship"] = sh

    over_ship = api("admin", "admin123").raw(
        "POST", f"/api/sales/orders/{so['id']}/ship",
        {"items": [{"product_id": st["p1"], "qty": 9999, "price": 150}]})
    st["over_ship_code"] = over_ship.status_code

    rec = admin.get("/api/finance/receivables", page_size=5)
    st["receivable"] = rec["items"][0]

    # ---- 财务：部分收款 -> 超额被拒 -> 全额核销；应付全额核销 ----
    rc = admin.post("/api/finance/receipts",
                    {"receivable_id": st["receivable"]["id"], "amount": 500})
    st["receipt"] = rc
    st["rec_partial"] = admin.get("/api/finance/receivables",
                                  keyword=st["receivable"]["receivable_no"])["items"][0]
    over_rc = api("admin", "admin123").raw(
        "POST", "/api/finance/receipts",
        {"receivable_id": st["receivable"]["id"], "amount": 99999})
    st["over_receipt_code"] = over_rc.status_code

    admin.post("/api/finance/receipts", {"receivable_id": st["receivable"]["id"], "amount": 400})
    st["rec_settled"] = admin.get("/api/finance/receivables",
                                  keyword=st["receivable"]["receivable_no"])["items"][0]

    opens = admin.get("/api/finance/payables", status="open", page_size=50)["items"]
    assert opens, "存在未核销应付"
    for p in opens:
        admin.post("/api/finance/payments", {"payable_id": p["id"], "amount": p["balance"]})
    st["payable_remain"] = admin.get("/api/finance/payables", status="open", page_size=50)["items"]

    # ---- 库存：调拨 + 盘点 ----
    tr = admin.post("/api/inventory/transfers", {
        "from_warehouse_id": st["w1"], "to_warehouse_id": st["w2"],
        "items": [{"product_id": st["p2"], "qty": 2}],
    })
    st["transfer"] = tr

    ck = admin.post("/api/inventory/checks",
                    {"warehouse_id": st["w1"], "product_ids": [st["p2"]]})
    admin.put(f"/api/inventory/checks/{ck['id']}",
              {"items": [{"product_id": st["p2"], "actual_qty": 0}]})
    st["check_done"] = admin.post(f"/api/inventory/checks/{ck['id']}/done")

    # ---- 审计 / 仪表盘 ----
    st["audit_items"] = admin.get("/api/system/audit-logs", page_size=100)["items"]
    st["dash_summary"] = admin.get("/api/dashboard/summary")
    st["dash_trend"] = admin.get("/api/dashboard/sales-trend", days=7)
    st["dash_top"] = admin.get("/api/dashboard/top-products", limit=5)
    st["dash_recent"] = admin.get("/api/dashboard/recent-orders", limit=5)
    return st


# ================= 认证 =================

class TestAuth:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200 and r.json()["status"] == "ok"

    def test_wrong_password(self, client):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.json()["code"] != 0

    def test_me_and_permissions(self, admin):
        assert admin.get("/api/auth/me")["username"] == "admin"
        perms = admin.get("/api/auth/permissions")
        assert "purchase:order:manage" in perms

    def test_invalid_token(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.here"})
        assert r.status_code == 401


# ================= RBAC =================

class TestRbac:
    def test_auditor_cannot_manage_master(self, api):
        r = api("auditor", "demo123").raw("POST", "/api/master/products",
                                          {"code": "X99", "name": "x", "category_id": 1,
                                           "spec": "", "unit": "个", "price": 1, "min_stock": 0})
        assert r.status_code == 403

    def test_keeper_cannot_create_purchase(self, api):
        r = api("keeper", "demo123").raw("POST", "/api/purchase/orders",
                                         {"supplier_id": 1, "warehouse_id": 1, "remark": "", "items": []})
        assert r.status_code == 403

    def test_finance_role_has_finance_perms(self, api):
        perms = api("finance", "demo123").get("/api/auth/permissions")
        assert "finance:read" in perms and "finance:manage" in perms

    def test_anonymous_rejected(self, client):
        r = client.get("/api/master/products")
        assert r.status_code == 401


# ================= 采购链路断言 =================

class TestPurchaseFlow:
    def test_draft_created(self, flow_state):
        assert flow_state["po"]["status"] == "draft"
        assert flow_state["po"]["total_amount"] == 2000
        assert flow_state["po_no"].startswith("PO") and "%" not in flow_state["po_no"]

    def test_approve_then_partial_receive(self, flow_state):
        assert flow_state["stock_in"]["total_amount"] == 1800
        assert flow_state["stock_p1_after"] - flow_state["stock_p1_before"] == 8
        assert flow_state["po_final_status"] == "completed"

    def test_payable_created(self, flow_state):
        assert flow_state["payable"]["total_amount"] == 1800
        assert flow_state["payable"]["status"] == "open"

    def test_over_receive_rejected(self, flow_state):
        assert flow_state["over_receive_code"] == 400
        assert "超过未收" in flow_state["over_receive_msg"]


# ================= 销售 + 财务断言 =================

class TestSalesFinanceFlow:
    def test_ship_and_receivable(self, flow_state):
        assert flow_state["so"]["total_amount"] == 900
        assert flow_state["ship"]["total_amount"] == 900
        assert flow_state["receivable"]["total_amount"] == 900

    def test_over_ship_rejected(self, flow_state):
        assert flow_state["over_ship_code"] == 400

    def test_partial_receipt(self, flow_state):
        assert flow_state["receipt"]["receipt_no"].startswith("RC")
        assert flow_state["rec_partial"]["status"] == "partial"

    def test_over_receipt_rejected(self, flow_state):
        assert flow_state["over_receipt_code"] == 400

    def test_all_settled(self, flow_state):
        assert flow_state["rec_settled"]["status"] == "settled"
        assert flow_state["payable_remain"] == [], "应付未全部核销"


# ================= 库存 / 审计 / 仪表盘断言 =================

class TestInventoryAndOps:
    def test_transfer(self, flow_state):
        assert flow_state["transfer"]["transfer_no"].startswith("TR")

    def test_check_cycle(self, flow_state):
        assert flow_state["check_done"]["status"] == "done"

    def test_audit_logs(self, flow_state):
        assert len(flow_state["audit_items"]) >= 15, "审计日志数量不足"

    def test_dashboard(self, flow_state):
        assert flow_state["dash_summary"]["today_sales"] >= 0
        assert len(flow_state["dash_trend"]["labels"]) == 7
        assert flow_state["dash_top"], "TOP 商品为空"
        assert flow_state["dash_recent"], "最近订单为空"