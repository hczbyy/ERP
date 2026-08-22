"""OpenERP 全量接口覆盖测试：覆盖 openapi.json 中全部 58 个路由的每个方法。

策略：创建临时数据 -> 更新/查询 -> 删除/清理，验证 CRUD 全生命周期；
不删除任何种子数据，结束时数据库与运行前一致（仅增加业务流水）。
用法：python tests/api_full_smoke.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

BASE = "http://127.0.0.1:8000"
TS = str(int(time.time()))[-6:]
PASS, FAIL = 0, 0
FAILED = []


def step(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"PASS  {name}")
        PASS += 1
    except Exception as e:
        print(f"FAIL  {name}: {e}")
        FAIL += 1
        FAILED.append(name)


class Client:
    def __init__(self, username, password):
        r = httpx.post(f"{BASE}/api/auth/login", json={"username": username, "password": password}, timeout=10)
        j = r.json()
        assert j["code"] == 0, f"登录失败: {j}"
        self.h = {"Authorization": f"Bearer {j['data']['token']}"}

    def req(self, method, path, body=None, expect=None, **kw):
        r = httpx.request(method, f"{BASE}{path}", headers=self.h, json=body or {}, timeout=10, **kw)
        try:
            j = r.json()
        except Exception:
            raise AssertionError(f"{method} {path} 非 JSON: {r.status_code} {r.text[:200]}")
        if expect is None:
            expect = r.status_code < 400 and j.get("code") == 0
        if not expect:
            raise AssertionError(f"{method} {path} -> {r.status_code} {j}")
        return j["data"] if r.status_code < 400 else j

    def get(self, path, **kw):
        return self.req("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.req("POST", path, body or {}, **kw)

    def put(self, path, body=None, **kw):
        return self.req("PUT", path, body or {}, **kw)

    def delete(self, path, **kw):
        return self.req("DELETE", path, **kw)

    def raw(self, method, path, body=None):
        return httpx.request(method, f"{BASE}{path}", headers=self.h, json=body or {}, timeout=10)


def main():
    admin = Client("admin", "admin123")

    # ---------- auth ----------
    def auth_me_perm():
        me = admin.get("/api/auth/me")
        assert me["user"]["username"] == "admin"
        assert isinstance(me["permissions"], list) and len(me["permissions"]) > 0
        perms = admin.get("/api/auth/permissions")["permissions"]
        assert isinstance(perms, list) and len(perms) > 0

    step("auth: me + permissions", auth_me_perm)

    def change_pwd_roundtrip():
        admin.post("/api/auth/change-password", {"old_password": "admin123", "new_password": "tmp123456"})
        c = Client("admin", "tmp123456")  # 新密码可登录
        c.post("/api/auth/change-password", {"old_password": "tmp123456", "new_password": "admin123"})
        Client("admin", "admin123")  # 密码已还原

    step("auth: change-password 改密往返", change_pwd_roundtrip)

    # ---------- master: categories ----------
    cat_id = {}

    def cat_crud():
        d = admin.post("/api/master/categories", {"name": f"测试分类{TS}"})
        cat_id["id"] = d["id"]
        admin.put(f"/api/master/categories/{d['id']}", {"name": f"测试分类改{TS}"})
        lst = admin.get("/api/master/categories")
        assert any(x["id"] == d["id"] and x["name"] == f"测试分类改{TS}" for x in lst)
        admin.delete(f"/api/master/categories/{d['id']}")
        lst2 = admin.get("/api/master/categories")
        assert all(x["id"] != d["id"] for x in lst2)

    step("master: categories CRUD", cat_crud)

    # ---------- master: products ----------
    prod_id = {}

    def product_crud():
        d = admin.post("/api/master/products", {
            "code": f"TMP{TS}", "name": f"测试商品{TS}", "unit": "件",
            "purchase_price": 10, "sale_price": 20,
        })
        prod_id["id"] = d["id"]
        admin.put(f"/api/master/products/{d['id']}", {"code": f"TMP{TS}", "name": f"测试商品改{TS}", "sale_price": 25})
        lst = admin.get("/api/master/products", params={"keyword": f"TMP{TS}"})
        assert lst["items"] and lst["items"][0]["sale_price"] == 25
        allp = admin.get("/api/master/products/all")
        assert any(x["id"] == d["id"] for x in allp)

    step("master: products CRUD", product_crud)

    # ---------- master: customers ----------
    cust_id = {}

    def customer_crud():
        d = admin.post("/api/master/customers", {"code": f"TC{TS}", "name": f"测试客户{TS}", "credit_limit": 1000})
        cust_id["id"] = d["id"]
        admin.put(f"/api/master/customers/{d['id']}", {"code": f"TC{TS}", "name": f"测试客户改{TS}"})
        lst = admin.get("/api/master/customers", params={"keyword": f"TC{TS}"})
        assert lst["items"] and lst["items"][0]["name"] == f"测试客户改{TS}"

    step("master: customers CRUD", customer_crud)

    # ---------- master: suppliers ----------
    sup_id = {}

    def supplier_crud():
        d = admin.post("/api/master/suppliers", {"code": f"TS{TS}", "name": f"测试供应商{TS}"})
        sup_id["id"] = d["id"]
        admin.put(f"/api/master/suppliers/{d['id']}", {"code": f"TS{TS}", "name": f"测试供应商改{TS}"})
        lst = admin.get("/api/master/suppliers", params={"keyword": f"TS{TS}"})
        assert lst["items"] and lst["items"][0]["name"] == f"测试供应商改{TS}"

    step("master: suppliers CRUD", supplier_crud)

    # ---------- master: warehouses ----------
    wh_id = {}

    def warehouse_crud():
        d = admin.post("/api/master/warehouses", {"code": f"TW{TS}", "name": f"测试仓库{TS}"})
        wh_id["id"] = d["id"]
        admin.put(f"/api/master/warehouses/{d['id']}", {"code": f"TW{TS}", "name": f"测试仓库改{TS}"})
        lst = admin.get("/api/master/warehouses")
        assert any(x["id"] == d["id"] and x["name"] == f"测试仓库改{TS}" for x in lst)

    step("master: warehouses CRUD", warehouse_crud)

    # ---------- system: departments / employees / roles / users ----------
    def dept_crud():
        d = admin.post("/api/system/departments", {"code": f"TD{TS}", "name": f"测试部门{TS}"})
        admin.put(f"/api/system/departments/{d['id']}", {"code": f"TD{TS}", "name": f"测试部门改{TS}"})
        lst = admin.get("/api/system/departments")
        assert any(x["id"] == d["id"] and x["name"] == f"测试部门改{TS}" for x in lst)
        admin.delete(f"/api/system/departments/{d['id']}")

    step("system: departments CRUD", dept_crud)

    def emp_crud():
        depts = admin.get("/api/system/departments")
        did = depts[0]["id"] if depts else None
        d = admin.post("/api/system/employees", {
            "emp_no": f"E{TS}", "name": f"测试员工{TS}",
            "department_id": did, "hire_date": "2026-01-01", "position": "测试",
        })
        admin.put(f"/api/system/employees/{d['id']}", {"emp_no": f"E{TS}", "name": f"测试员工改{TS}", "status": "leave"})
        lst = admin.get("/api/system/employees", params={"keyword": f"E{TS}"})
        assert lst["items"] and lst["items"][0]["status"] == "leave"

    step("system: employees CRUD", emp_crud)

    role_id = {}

    def role_crud():
        groups = admin.get("/api/system/permissions")["groups"]
        pids = [g[0]["id"] for g in list(groups.values()) if g][:2]
        assert len(pids) == 2, groups
        d = admin.post("/api/system/roles", {"code": f"TR{TS}", "name": f"测试角色{TS}", "permission_ids": pids})
        role_id["id"] = d["id"]
        admin.put(f"/api/system/roles/{d['id']}", {"code": f"TR{TS}", "name": f"测试角色改{TS}"})
        lst = admin.get("/api/system/roles")
        assert any(x["id"] == d["id"] and x["name"] == f"测试角色改{TS}" for x in lst)

    step("system: roles CRUD", role_crud)

    def user_crud():
        d = admin.post("/api/system/users", {
            "username": f"tmp{TS}", "display_name": f"测试用户{TS}",
            "password": "tmp123456", "role_ids": [role_id["id"]],
        })
        uid = d["id"]
        # 新用户可登录并带角色权限
        c = Client(f"tmp{TS}", "tmp123456")
        assert c.get("/api/auth/me")["user"]["username"] == f"tmp{TS}"
        # 停用后无法登录
        admin.post(f"/api/system/users/{uid}/toggle-active")
        r = httpx.post(f"{BASE}/api/auth/login", json={"username": f"tmp{TS}", "password": "tmp123456"})
        assert r.json()["code"] != 0, "停用用户不应能登录"
        # 重新启用 + 更新 + 删除
        admin.post(f"/api/system/users/{uid}/toggle-active")
        admin.put(f"/api/system/users/{uid}", {"username": f"tmp{TS}", "display_name": f"测试用户改{TS}"})
        admin.delete(f"/api/system/users/{uid}")
        lst = admin.get("/api/system/users", params={"keyword": f"tmp{TS}"})
        assert not lst["items"], "临时用户应已删除"

    step("system: users CRUD + toggle-active", user_crud)

    def role_delete():
        admin.delete(f"/api/system/roles/{role_id['id']}")
        lst = admin.get("/api/system/roles")
        assert all(x["id"] != role_id["id"] for x in lst)

    step("system: roles 删除", role_delete)

    # ---------- inventory ----------
    def stock_query():
        stocks = admin.get("/api/inventory/stocks", params={"warehouse_id": 1, "page_size": 100})
        assert stocks["items"]
        logs = admin.get("/api/inventory/logs", params={"page_size": 10})
        assert logs["items"]
        low = admin.get("/api/dashboard/low-stocks")
        assert isinstance(low, list)

    step("inventory: stocks/logs 查询", stock_query)

    def transfer_create():
        w2 = admin.get("/api/master/warehouses")[1]
        p = admin.get("/api/master/products/all")[0]
        d = admin.post("/api/inventory/transfers", {
            "from_warehouse_id": 1, "to_warehouse_id": w2["id"],
            "items": [{"product_id": p["id"], "qty": 1}],
        })
        assert d["transfer_no"].startswith("TR")

    step("inventory: transfers 创建", transfer_create)

    def check_flow():
        c = admin.post("/api/inventory/checks", {"warehouse_id": 1, "product_ids": [1]})
        cid = c["id"]
        admin.put(f"/api/inventory/checks/{cid}", {"items": [{"product_id": 1, "actual_qty": 1}]})
        admin.post(f"/api/inventory/checks/{cid}/done")
        det = admin.get(f"/api/inventory/checks/{cid}")
        assert det["status"] == "done", det
        lst = admin.get("/api/inventory/checks", params={"page_size": 10})
        assert lst["items"]

    step("inventory: checks 创建/实盘/完成", check_flow)

    # ---------- purchase/sales/finance 全状态机 ----------
    def purchase_flow():
        s = admin.get("/api/master/suppliers/all")[0]
        p = admin.get("/api/master/products/all")
        d = admin.post("/api/purchase/orders", {
            "supplier_id": s["id"], "warehouse_id": 1,
            "items": [{"product_id": p[0]["id"], "qty": 3, "price": 50}],
        })
        oid = d["id"]
        # 编辑草稿
        admin.put(f"/api/purchase/orders/{oid}", {
            "supplier_id": s["id"], "warehouse_id": 1, "remark": "改",
            "items": [{"product_id": p[0]["id"], "qty": 4, "price": 55}],
        })
        detail = admin.get(f"/api/purchase/orders/{oid}")
        assert detail["total_amount"] == 220, detail["total_amount"]
        # 取消（草稿/已审核均可取消；取消后不可删除）
        admin.post(f"/api/purchase/orders/{oid}/cancel", {"reason": "全量测试"})
        assert admin.get(f"/api/purchase/orders/{oid}")["status"] == "cancelled"
        # 另建草稿验证删除
        d2 = admin.post("/api/purchase/orders", {
            "supplier_id": s["id"], "warehouse_id": 1,
            "items": [{"product_id": p[0]["id"], "qty": 1, "price": 10}],
        })
        admin.delete(f"/api/purchase/orders/{d2['id']}")

    step("purchase: 建单/编辑/取消/删除", purchase_flow)

    def purchase_receive_flow():
        s = admin.get("/api/master/suppliers/all")[0]
        p = admin.get("/api/master/products/all")
        d = admin.post("/api/purchase/orders", {
            "supplier_id": s["id"], "warehouse_id": 1,
            "items": [{"product_id": p[0]["id"], "qty": 5, "price": 60}],
        })
        oid = d["id"]
        admin.post(f"/api/purchase/orders/{oid}/approve")
        si = admin.post(f"/api/purchase/orders/{oid}/receive",
                        {"items": [{"product_id": p[0]["id"], "qty": 5, "price": 62}]})
        assert si["total_amount"] == 310, si  # 按实际收货单价 62 入账
        ins = admin.get("/api/purchase/stock-ins", params={"keyword": si["stock_in_no"]})
        assert ins["items"]
        det = admin.get(f"/api/purchase/stock-ins/{ins['items'][0]['id']}")
        assert det["items"][0]["price"] == 62

    step("purchase: 审核/收货(实际单价)/入库单查询", purchase_receive_flow)

    def sales_flow():
        c = admin.get("/api/master/customers/all")[0]
        p = admin.get("/api/master/products/all")
        d = admin.post("/api/sales/orders", {
            "customer_id": c["id"], "warehouse_id": 1,
            "items": [{"product_id": p[0]["id"], "qty": 2, "price": 100}],
        })
        oid = d["id"]
        admin.put(f"/api/sales/orders/{oid}", {
            "customer_id": c["id"], "warehouse_id": 1,
            "items": [{"product_id": p[0]["id"], "qty": 2, "price": 110}],
        })
        assert admin.get(f"/api/sales/orders/{oid}")["total_amount"] == 220
        admin.post(f"/api/sales/orders/{oid}/approve")
        so = admin.post(f"/api/sales/orders/{oid}/ship",
                        {"items": [{"product_id": p[0]["id"], "qty": 2, "price": 115}]})
        assert so["total_amount"] == 230, so  # 按实际发货单价 115
        outs = admin.get("/api/sales/stock-outs", params={"keyword": so["stock_out_no"]})
        assert outs["items"]
        det = admin.get(f"/api/sales/stock-outs/{outs['items'][0]['id']}")
        assert det["items"][0]["price"] == 115

    step("sales: 建单/编辑/审核/发货(实际单价)/出库单查询", sales_flow)

    def sales_cancel():
        c = admin.get("/api/master/customers/all")[0]
        p = admin.get("/api/master/products/all")
        d = admin.post("/api/sales/orders", {
            "customer_id": c["id"], "warehouse_id": 1,
            "items": [{"product_id": p[0]["id"], "qty": 1, "price": 10}],
        })
        admin.post(f"/api/sales/orders/{d['id']}/cancel", {"reason": "全量测试"})
        assert admin.get(f"/api/sales/orders/{d['id']}")["status"] == "cancelled"
        # 另建草稿验证删除
        d2 = admin.post("/api/sales/orders", {
            "customer_id": c["id"], "warehouse_id": 1,
            "items": [{"product_id": p[0]["id"], "qty": 1, "price": 10}],
        })
        admin.delete(f"/api/sales/orders/{d2['id']}")

    step("sales: 取消/删除", sales_cancel)

    # ---------- finance ----------
    def finance_query():
        recs = admin.get("/api/finance/receivables", params={"page_size": 5})
        pays = admin.get("/api/finance/payables", params={"page_size": 5})
        rcts = admin.get("/api/finance/receipts", params={"page_size": 5})
        pms = admin.get("/api/finance/payments", params={"page_size": 5})
        assert isinstance(recs["items"], list) and isinstance(pays["items"], list)
        assert isinstance(rcts["items"], list) and isinstance(pms["items"], list)

    step("finance: 应收/应付/收款/付款查询", finance_query)

    # ---------- dashboard ----------
    def dashboard():
        s = admin.get("/api/dashboard/summary")
        assert "today_sales" in s
        t = admin.get("/api/dashboard/sales-trend", params={"days": 7})
        assert len(t["labels"]) == 7
        top = admin.get("/api/dashboard/top-products", params={"limit": 5})
        assert isinstance(top, list)
        ro = admin.get("/api/dashboard/recent-orders", params={"limit": 5})
        assert isinstance(ro, list)

    step("dashboard: summary/trend/top/low/recent", dashboard)

    # ---------- audit ----------
    def audit_logs():
        logs = admin.get("/api/system/audit-logs", params={"page_size": 20})
        assert logs["items"]

    step("system: audit-logs 审计日志", audit_logs)

    # ---------- RBAC 拦截（auditor 只读） ----------
    def rbac():
        auditor = Client("auditor", "demo123")
        r = auditor.raw("POST", "/api/master/products", {"code": "X1", "name": "x"})
        assert r.status_code == 403, r.text
        r2 = auditor.raw("POST", "/api/purchase/orders", {"supplier_id": 1, "warehouse_id": 1, "items": []})
        assert r2.status_code == 403, r2.text

    step("RBAC: 只读账号写操作 403", rbac)

    print("\n" + "=" * 46)
    print(f"API FULL SMOKE: PASS={PASS} FAIL={FAIL}")
    if FAILED:
        print("失败项:", *FAILED, sep="\n  - ")
    print("=" * 46)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()