# -*- coding: utf-8 -*-
"""最小复现：浏览器打开库存查询/流水页，抓 422 请求的完整 URL 与响应体。"""
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CAPTURE_JS = r"""
(function(){
  if (window.__cap) return;
  window.__cap = { req: [], err: [] };
  const cap = window.__cap;
  const fmt = (a) => a.map(x => { try { return (x instanceof Error) ? x.message : (typeof x === 'string' ? x : JSON.stringify(x)); } catch(e){ return String(x); } }).join(' | ');
  const origErr = console.error;
  console.error = function(...a){ cap.err.push({t: Date.now(), msg: fmt(a)}); return origErr.apply(console, a); };
  const record = (method, url, status, body) => cap.req.push({ method, url, status, body: (body||'').slice(0, 500) });
  const origFetch = window.fetch;
  window.fetch = function(...args){
    const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || String(args[0]);
    const method = (args[1] && args[1].method) || 'GET';
    return origFetch.apply(this, args).then(r => {
      if (r.status >= 400 || url.includes('/api/')) {
        r.clone().text().then(t => record(method, url, r.status, t)).catch(() => record(method, url, r.status, ''));
      }
      return r;
    });
  };
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m, u){ this.__u = String(u); this.__m = m; return origOpen.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function(){
    this.addEventListener('loadend', () => { if (this.status >= 400) record(this.__m, this.__u, this.status, this.responseText || ''); });
    return origSend.apply(this, arguments);
  };
})();
"""

BASE = "http://127.0.0.1:8000"

opts = Options()
opts.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
opts.add_argument("--headless=new")
opts.add_argument("--window-size=1600,900")
opts.add_argument("--disable-gpu")
opts.add_argument("--no-sandbox")
opts.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})

driver = webdriver.Edge(options=opts)
driver.set_page_load_timeout(30)

try:
    driver.get(BASE)
    time.sleep(2)
    driver.execute_script(CAPTURE_JS)
    time.sleep(0.5)

    driver.find_element(By.ID, "login-username").send_keys("admin")
    driver.find_element(By.ID, "login-password").send_keys("admin123")
    driver.find_element(By.ID, "login-btn").click()
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#app-view:not(.hidden)")))
    time.sleep(2)

    # 库存查询
    driver.execute_script('location.hash = "#/stocks";')
    time.sleep(3)
    # 库存流水
    driver.execute_script('location.hash = "#/stock-logs";')
    time.sleep(3)

    cap = json.loads(driver.execute_script(
        "var c = window.__cap; window.__cap = {req:[],err:[]}; return JSON.stringify(c);"))
    print("==== console errors ====")
    for e in cap["err"]:
        print("ERR:", e["msg"][:300])
    print("==== requests (status>=400 or /api/) ====")
    for r in cap["req"]:
        print(f"{r['status']} {r['method']} {r['url']}")
        if r["status"] >= 400:
            print("   BODY:", r["body"][:400])

    # 浏览器日志（资源加载失败等）
    print("==== browser log SEVERE ====")
    for e in driver.get_log("browser"):
        if e.get("level") == "SEVERE":
            print(e.get("message", "")[:400])
finally:
    driver.quit()
print("DONE")