# -*- coding: utf-8 -*-
"""
OpenERP 前端浏览器全量验证脚本（Selenium + Edge WebDriver）
- 全程 console 监听（CDP browser log + JS 注入捕获，含堆栈）
- 全程网络监听（CDP performance log + fetch/XHR 包装，记录 4xx/5xx）
- 每页截图到 screenshots 目录并校验文件存在
"""
import os, sys, json, time, traceback

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://127.0.0.1:8000"
WORK = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(WORK, "screenshots")
REPORT = os.path.join(WORK, "report.json")
LOGF = os.path.join(WORK, "browser_verify.log")
os.makedirs(SHOT_DIR, exist_ok=True)

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

CAPTURE_JS = r"""
(function(){
  if (window.__vcap) return;
  window.__vcap = { errors: [], warns: [], net: [], log: [] };
  const cap = window.__vcap;
  const fmt = (a) => a.map(x => {
    try {
      if (typeof x === 'string') return x;
      if (x instanceof Error) return x.name + ': ' + x.message + (x.stack ? ' || ' + x.stack : '');
      return JSON.stringify(x);
    } catch(e){ return String(x); }
  }).join(' | ');
  const origErr = console.error, origWarn = console.warn, origLog = console.log;
  console.error = function(...a){ cap.errors.push({ t: Date.now(), msg: fmt(a) }); return origErr.apply(console, a); };
  console.warn  = function(...a){ cap.warns.push({ t: Date.now(), msg: fmt(a) }); return origWarn.apply(console, a); };
  console.log   = function(...a){ cap.log.push({ t: Date.now(), msg: fmt(a) }); return origLog.apply(console, a); };
  const origFetch = window.fetch;
  window.fetch = function(...args){
    const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || String(args[0]);
    const method = (args[1] && args[1].method) || 'GET';
    return origFetch.apply(this, args).then(r => {
      if (r.status >= 400) cap.net.push({ t: Date.now(), url: url, status: r.status, method: method });
      return r;
    });
  };
  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m, u){ 
    this.addEventListener('loadend', () => { if (this.status >= 400) cap.net.push({ t: Date.now(), url: String(u), status: this.status, method: m }); });
    return origOpen.apply(this, arguments);
  };
})();
"""

def log(msg):
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def drain_browser_log():
    """读取 CDP browser 日志（只读一次，读取即清空），返回 (errors, warns)"""
    errors, warns = [], []
    try:
        for e in driver.get_log("browser"):
            if e.get("level") == "SEVERE":
                errors.append(e.get("message", ""))
            elif e.get("level") == "WARNING":
                warns.append(e.get("message", ""))
    except Exception as ex:
        errors.append("[browser-log-unavailable] " + str(ex))
    return errors, warns

def drain_perf_log():
    """读取 performance 日志中的 Network.responseReceived，返回 >=400 的 (url, status) 列表"""
    issues = []
    try:
        for e in driver.get_log("performance"):
            msg = e.get("message", "")
            if "responseReceived" not in msg:
                continue
            try:
                obj = json.loads(msg)
                inner = obj.get("message", obj)
                params = inner.get("params", {})
                resp = params.get("response", {})
                st = resp.get("status", 0)
                if isinstance(st, int) and st >= 400:
                    issues.append({"url": resp.get("url", ""), "status": st})
            except Exception:
                pass
    except Exception as ex:
        issues.append({"url": "", "status": "[perf-log-unavailable] " + str(ex)})
    return issues

def drain_capture():
    js = ("var e=window.__vcap?window.__vcap.errors:[];var w=window.__vcap?window.__vcap.warns:[];"
          "var n=window.__vcap?window.__vcap.net:[];"
          "window.__vcap&&(window.__vcap.errors=[],window.__vcap.warns=[],window.__vcap.net=[]);"
          "return JSON.stringify({errors:e,warns:w,net:n});")
    try:
        raw = driver.execute_script(js)
        return json.loads(raw)
    except Exception as ex:
        return {"errors": ["[capture-unavailable] " + str(ex)], "warns": [], "net": []}

def shot(name, page):
    path = os.path.join(SHOT_DIR, name)
    try:
        driver.save_screenshot(path)
    except Exception as ex:
        return {"file": name, "page": page, "saved": False, "error": str(ex)}
    ok = os.path.exists(path)
    size = os.path.getsize(path) if ok else 0
    log(f"截图 {name} (page={page}) -> saved={ok} size={size}")
    return {"file": name, "page": page, "saved": ok, "size": size}

def page_state():
    js = """
    const content = document.getElementById('content');
    if (!content) return { rendered: false };
    const title = (document.getElementById('page-title')||{}).textContent || '';
    let tables = content.querySelectorAll('table.table');
    let rows = 0, empty = false, emptyTexts = [];
    tables.forEach(t => {
        const b = t.querySelector('tbody');
        if (!b) return;
        const hasEmpty = !!b.querySelector('.empty');
        if (hasEmpty) { empty = true; const e = b.querySelector('.empty'); emptyTexts.push((e.textContent||'').trim()); }
        else rows += b.querySelectorAll('tr').length;
    });
    const cards = content.querySelectorAll('.card').length;
    const canvases = content.querySelectorAll('canvas').length;
    const statCards = content.querySelectorAll('.stat-card').length;
    const emptyMsg = content.querySelector('.empty') ? (content.querySelector('.empty').textContent||'').trim() : '';
    return { rendered: true, title, tables: tables.length, rows, empty, emptyTexts, cards, canvases, statCards, emptyMsg };
    """
    return driver.execute_script(js)

def modal_info():
    js = """
    const masks = document.querySelectorAll('#modal-root .modal-mask');
    if (!masks.length) return { open: false };
    const m = masks[masks.length-1];
    const title = (m.querySelector('.modal-title')||{}).textContent || '';
    const labels = [...m.querySelectorAll('.modal-body label')].map(l => (l.textContent||'').trim()).filter(Boolean);
    const ths = [...m.querySelectorAll('.modal-body th')].map(t => (t.textContent||'').trim()).filter(Boolean);
    const inputs = [...m.querySelectorAll('.modal-body input')].map(i => ({ type: i.type, placeholder: i.placeholder||'', id: i.id||'' }));
    const selects = [...m.querySelectorAll('.modal-body select')].map(s => ({ id: s.id||'', options: s.options.length, firstLabel: s.options.length>1 ? s.options[1].textContent.trim() : '' }));
    const textareas = m.querySelectorAll('.modal-body textarea').length;
    const footBtns = [...m.querySelectorAll('.modal-foot button')].map(b => (b.textContent||'').trim());
    const closeBtn = !!m.querySelector('.modal-close');
    return { open: true, title, labels, ths, inputs, selects, textareas, footBtns, closeBtn };
    """
    return driver.execute_script(js)

def goto(hash_, name, shot_name, wait=2.5, drain=True):
    log(f"==> 进入页面 {name} ({hash_})")
    try:
        try:
            el = driver.find_element(By.CSS_SELECTOR, f'.menu-item[data-hash="{hash_}"]')
            el.click()
        except Exception:
            driver.execute_script(f'location.hash = "{hash_}";')
    except Exception as ex:
        log(f"    导航异常: {ex}")
    time.sleep(wait)
    st = page_state()
    shot_info = shot(shot_name, name)
    rec = {"name": name, "hash": hash_, "state": st, "screenshot": shot_info}
    if drain:
        b_err, b_warn = drain_browser_log()
        p_issues = drain_perf_log()
        cap = drain_capture()
        rec["console_errors"] = b_err + cap["errors"]
        rec["console_warns"] = b_warn + cap["warns"]
        rec["net_issues"] = p_issues + cap["net"]
    else:
        rec["console_errors"] = []
        rec["console_warns"] = []
        rec["net_issues"] = []
    results.append(rec)
    log(f"    渲染={st.get('rendered')} title={st.get('title')} 行数={st.get('rows')} 空={st.get('empty')} "
        f"cards={st.get('cards')} canvas={st.get('canvases')} statCards={st.get('statCards')}")
    if rec["console_errors"]:
        log(f"    console 错误 {len(rec['console_errors'])} 条: " + " || ".join(rec["console_errors"][:5]))
    if rec["net_issues"]:
        log(f"    网络 4xx/5xx {len(rec['net_issues'])} 条: " + " || ".join(str(x) for x in rec["net_issues"][:8]))
    return rec

results = []

# ---------- 启动浏览器 ----------
# 由 Selenium Manager 自动下载与 Edge 版本匹配的 msedgedriver
opts = Options()
opts.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
opts.add_argument("--headless=new")
opts.add_argument("--window-size=1600,900")
opts.add_argument("--disable-gpu")
opts.add_argument("--no-sandbox")
opts.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})

driver = None
try:
    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(30)
    driver.set_window_size(1600, 900)
except Exception as ex:
    log("启动 headless 失败: " + str(ex) + "，回退到有头模式")
    try:
        opts2 = Options()
        opts2.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        opts2.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
        driver = webdriver.Edge(options=opts2)
        driver.set_page_load_timeout(30)
        driver.set_window_size(1600, 900)
    except Exception as ex2:
        log("浏览器启动彻底失败: " + str(ex2))
        sys.exit(1)

log("浏览器启动成功")

try:
    # ---------- 1. 登录页 ----------
    log("==> 打开登录页")
    driver.get(BASE)
    time.sleep(2.5)
    driver.execute_script(CAPTURE_JS)
    time.sleep(1)
    login_state = {
        "login_view_visible": driver.execute_script(
            "return !document.getElementById('login-view').classList.contains('hidden')"),
        "username_present": bool(driver.find_elements(By.ID, "login-username")),
        "password_present": bool(driver.find_elements(By.ID, "login-password")),
        "btn_present": bool(driver.find_elements(By.ID, "login-btn")),
        "title_text": driver.execute_script(
            "return (document.querySelector('.login-title')||{}).textContent || ''"),
    }
    shot("01_login.png", "登录页")
    b_err, b_warn = drain_browser_log()
    p_issues = drain_perf_log()
    cap = drain_capture()
    results.append({"name": "登录页", "hash": BASE, "state": login_state,
                    "console_errors": b_err + cap["errors"], "console_warns": b_warn + cap["warns"],
                    "net_issues": p_issues + cap["net"], "screenshot": {"file": "01_login.png", "page": "登录页"}})
    log(f"登录页可见={login_state['login_view_visible']} 标题={login_state['title_text']} "
        f"console错误={len(b_err+cap['errors'])} 网络4xx/5xx={len(p_issues+cap['net'])}")

    # ---------- 2. 登录 ----------
    log("==> 登录 admin/admin123")
    driver.find_element(By.ID, "login-username").send_keys("admin")
    driver.find_element(By.ID, "login-password").send_keys("admin123")
    driver.find_element(By.ID, "login-btn").click()
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#app-view:not(.hidden)")))
    except Exception:
        log("    等待主界面出现超时")
    time.sleep(2.5)
    dash = page_state()
    dash_state = {
        "rendered": dash.get("rendered"),
        "title": dash.get("title"),
        "stat_cards": dash.get("statCards"),
        "canvases": dash.get("canvases"),
        "cards": dash.get("cards"),
        "rows": dash.get("rows"),
        "user_text": driver.execute_script("return (document.getElementById('topbar-user')||{}).textContent || ''"),
        "stat_values": driver.execute_script(
            "return [...document.querySelectorAll('.stat-value')].map(e => e.textContent.trim())"),
    }
    shot("02_dashboard.png", "仪表盘")
    b_err, b_warn = drain_browser_log()
    p_issues = drain_perf_log()
    cap = drain_capture()
    results.append({"name": "仪表盘", "hash": "#/dashboard", "state": dash_state,
                    "console_errors": b_err + cap["errors"], "console_warns": b_warn + cap["warns"],
                    "net_issues": p_issues + cap["net"], "screenshot": {"file": "02_dashboard.png", "page": "仪表盘"}})
    log(f"仪表盘: 统计卡={dash_state['stat_cards']} 图表canvas={dash_state['canvases']} 用户={dash_state['user_text']} "
        f"统计值={dash_state['stat_values']} console错误={len(b_err+cap['errors'])}")

    # ---------- 3. 基础数据 ----------
    goto("#/products", "基础数据-商品", "03_products.png")
    goto("#/customers", "基础数据-客户", "04_customers.png")
    goto("#/suppliers", "基础数据-供应商", "05_suppliers.png")
    goto("#/warehouses", "基础数据-仓库", "06_warehouses.png")

    # ---------- 4. 采购管理 ----------
    goto("#/purchase-orders", "采购管理-采购订单", "07_purchase_orders.png")
    goto("#/stock-ins", "采购管理-收货入库", "08_stock_ins.png")

    # ---------- 5. 销售管理 ----------
    goto("#/sales-orders", "销售管理-销售订单", "09_sales_orders.png")
    goto("#/stock-outs", "销售管理-发货出库", "10_stock_outs.png")

    # ---------- 6. 库存管理 ----------
    goto("#/stocks", "库存管理-库存查询", "11_stocks.png")
    goto("#/transfers", "库存管理-库存调拨", "12_transfers.png")
    goto("#/checks", "库存管理-盘点管理", "13_checks.png")
    goto("#/stock-logs", "库存管理-库存流水(补充)", "14_stock_logs.png")

    # ---------- 7. 财务管理 ----------
    goto("#/receivables", "财务管理-应收", "15_receivables.png")
    goto("#/payables", "财务管理-应付", "16_payables.png")
    goto("#/receipts", "财务管理-收款单", "17_receipts.png")
    goto("#/payments", "财务管理-付款单", "18_payments.png")

    # ---------- 8. 系统管理 ----------
    goto("#/users", "系统管理-用户", "19_users.png")
    goto("#/roles", "系统管理-角色", "20_roles.png")
    goto("#/departments", "系统管理-部门", "21_departments.png")
    goto("#/employees", "系统管理-员工", "22_employees.png")
    goto("#/audit-logs", "系统管理-审计日志", "23_audit_logs.png")

    # ============ 重点交互 ============

    # ---------- a. 采购订单新建弹窗 ----------
    log("==> 交互a: 采购订单-新建采购单弹窗")
    goto("#/purchase-orders", "采购订单(交互准备)", None, wait=2.5, drain=True)
    try:
        add_btn = driver.find_element(By.ID, "add-btn")
        add_btn.click()
        time.sleep(1.5)
        mi = modal_info()
        shot("24_po_new_dialog_open.png", "采购订单-新建弹窗(打开)")
        # 选商品
        sel = Select(driver.find_element(By.CSS_SELECTOR, "#modal-root .item-editor tbody tr select"))
        sel.select_by_index(1)  # 第一个真实商品
        time.sleep(0.8)
        price_val = driver.execute_script(
            "return document.querySelector('#modal-root .item-editor tbody tr input.num').value")
        product_label = driver.execute_script(
            "return document.querySelector('#modal-root .item-editor tbody tr select').selectedOptions[0].textContent.trim()")
        qty_inp = driver.find_element(By.CSS_SELECTOR, "#modal-root .item-editor tbody tr input.num")
        qty_inp.clear()
        qty_inp.send_keys("2")
        time.sleep(0.8)
        amt_val = driver.execute_script(
            "return document.querySelector('#modal-root .item-editor tbody tr td.amt').textContent.trim()")
        total_val = driver.execute_script(
            "return document.querySelector('#modal-root .item-editor tfoot #total').textContent.trim()")
        shot("25_po_new_dialog_filled.png", "采购订单-新建弹窗(选商品填数量)")
        po_dialog = {
            "modal": mi,
            "selected_product": product_label,
            "auto_price": price_val,
            "qty_input": "2",
            "row_amount": amt_val,
            "editor_total": total_val,
            "expected_total": None,  # 由 auto_price 计算
        }
        # 关闭弹窗
        cancel_btn = driver.find_element(By.CSS_SELECTOR, '#modal-root .modal-foot button[data-act="no"]')
        cancel_btn.click()
        time.sleep(0.8)
        po_dialog["closed"] = not driver.execute_script(
            "return document.querySelectorAll('#modal-root .modal-mask').length > 0")
        results.append({"name": "交互a-采购订单新建弹窗", "hash": "#/purchase-orders",
                        "state": po_dialog,
                        "console_errors": drain_browser_log()[0] + drain_capture()["errors"],
                        "console_warns": drain_browser_log()[1] + drain_capture()["warns"],
                        "net_issues": drain_perf_log() + drain_capture()["net"],
                        "screenshot": {"file": "24_po_new_dialog_open.png", "page": "采购订单新建弹窗"}})
        log(f"    弹窗标题={mi['title']} 字段labels={mi['labels']} 商品={product_label} 自动单价={price_val} "
            f"数量=2 行金额={amt_val} 合计={total_val} 关闭后弹窗存在={not po_dialog['closed']}")
    except Exception as ex:
        log("交互a 异常: " + traceback.format_exc())
        results.append({"name": "交互a-采购订单新建弹窗", "hash": "#/purchase-orders",
                        "state": {"error": str(ex)}, "console_errors": [], "console_warns": [],
                        "net_issues": [], "screenshot": {"file": "24_po_new_dialog_open.png", "page": "采购订单新建弹窗", "saved": False, "error": str(ex)}})

    # ---------- b. 商品页新建弹窗 ----------
    log("==> 交互b: 商品页-新建弹窗")
    goto("#/products", "商品(交互准备)", None, wait=2.5, drain=True)
    try:
        driver.find_element(By.ID, "add-btn").click()
        time.sleep(1.5)
        mi = modal_info()
        shot("26_product_new_dialog.png", "商品-新建弹窗")
        driver.find_element(By.CSS_SELECTOR, '#modal-root .modal-foot button[data-act="no"]').click()
        time.sleep(0.8)
        closed = not driver.execute_script(
            "return document.querySelectorAll('#modal-root .modal-mask').length > 0")
        results.append({"name": "交互b-商品新建弹窗", "hash": "#/products",
                        "state": {"modal": mi, "closed": closed},
                        "console_errors": drain_browser_log()[0] + drain_capture()["errors"],
                        "console_warns": drain_browser_log()[1] + drain_capture()["warns"],
                        "net_issues": drain_perf_log() + drain_capture()["net"],
                        "screenshot": {"file": "26_product_new_dialog.png", "page": "商品新建弹窗"}})
        log(f"    弹窗标题={mi['title']} 字段={mi['labels']} 关闭={closed}")
    except Exception as ex:
        log("交互b 异常: " + traceback.format_exc())
        results.append({"name": "交互b-商品新建弹窗", "hash": "#/products",
                        "state": {"error": str(ex)}, "console_errors": [], "console_warns": [],
                        "net_issues": [], "screenshot": {"file": "26_product_new_dialog.png", "page": "商品新建弹窗", "saved": False, "error": str(ex)}})

    # ---------- c. 财务应收收款弹窗 ----------
    log("==> 交互c: 应收-收款弹窗")
    goto("#/receivables", "应收(交互准备)", None, wait=2.5, drain=True)
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, "#content tbody button.btn-link")
        rec_btns = [b for b in btns if "收款" in b.text]
        if not rec_btns:
            st = page_state()
            results.append({"name": "交互c-应收收款弹窗", "hash": "#/receivables",
                            "state": {"found": False, "reason": "页面上没有「收款」按钮", "page_state": st},
                            "console_errors": [], "console_warns": [], "net_issues": [],
                            "screenshot": {"file": "27_receivable_collect_dialog.png", "page": "应收收款弹窗", "saved": False, "error": "无收款按钮"}})
            log("    未找到「收款」按钮，记录页面状态: " + json.dumps(st, ensure_ascii=False))
        else:
            rec_btns[0].click()
            time.sleep(1.2)
            mi = modal_info()
            shot("27_receivable_collect_dialog.png", "应收-收款弹窗")
            driver.find_element(By.CSS_SELECTOR, '#modal-root .modal-foot button[data-act="no"]').click()
            time.sleep(0.8)
            closed = not driver.execute_script(
                "return document.querySelectorAll('#modal-root .modal-mask').length > 0")
            results.append({"name": "交互c-应收收款弹窗", "hash": "#/receivables",
                            "state": {"found": True, "modal": mi, "closed": closed},
                            "console_errors": drain_browser_log()[0] + drain_capture()["errors"],
                            "console_warns": drain_browser_log()[1] + drain_capture()["warns"],
                            "net_issues": drain_perf_log() + drain_capture()["net"],
                            "screenshot": {"file": "27_receivable_collect_dialog.png", "page": "应收收款弹窗"}})
            log(f"    弹窗标题={mi['title']} 字段={mi['labels']} 关闭={closed}")
    except Exception as ex:
        log("交互c 异常: " + traceback.format_exc())
        results.append({"name": "交互c-应收收款弹窗", "hash": "#/receivables",
                        "state": {"error": str(ex)}, "console_errors": [], "console_warns": [],
                        "net_issues": [], "screenshot": {"file": "27_receivable_collect_dialog.png", "page": "应收收款弹窗", "saved": False, "error": str(ex)}})

    # 收尾：最后一次排空
    tail_err, tail_warn = drain_browser_log()
    tail_net = drain_perf_log()
    tail_cap = drain_capture()
    if tail_err or tail_warn or tail_net or tail_cap["errors"] or tail_cap["warns"] or tail_cap["net"]:
        results.append({"name": "收尾(未归属)", "hash": "",
                        "state": {},
                        "console_errors": tail_err + tail_cap["errors"],
                        "console_warns": tail_warn + tail_cap["warns"],
                        "net_issues": tail_net + tail_cap["net"],
                        "screenshot": None})

except Exception as ex:
    log("主流程异常: " + traceback.format_exc())
    try:
        shot("99_error.png", "异常现场")
    except Exception:
        pass
finally:
    if driver:
        try:
            driver.quit()
        except Exception:
            pass

with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
log(f"报告已写入 {REPORT}，共 {len(results)} 条记录")
print("DONE")