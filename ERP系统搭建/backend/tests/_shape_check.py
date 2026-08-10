# -*- coding: utf-8 -*-
"""临时：检查各接口返回结构"""
import httpx

B = "http://127.0.0.1:8000"
h = {"Authorization": "Bearer " + httpx.post(B + "/api/auth/login",
     json={"username": "admin", "password": "admin123"}).json()["data"]["token"]}


def shape(p, params=None):
    j = httpx.get(B + p, headers=h, params=params, timeout=10).json()
    d = j.get("data")
    if isinstance(d, dict):
        keys = list(d.keys())[:6]
        items_type = type(d.get("items")).__name__ if "items" in d else "-"
        print(f"{p:50s} -> dict keys={keys} items={items_type} total={d.get('total','-')}")
    else:
        print(f"{p:50s} -> {type(d).__name__} len={len(d) if hasattr(d, '__len__') else '?'}")
        if d:
            print("      first:", d[0])


shape("/api/master/warehouses")
shape("/api/master/products")
shape("/api/master/customers")
shape("/api/master/suppliers")
shape("/api/master/categories")
shape("/api/inventory/stocks", {"page": 1, "page_size": 10})
shape("/api/inventory/stocks", {"warehouse_id": 1, "page_size": 100})
shape("/api/inventory/logs", {"page": 1, "page_size": 10})
shape("/api/purchase/orders", {"page": 1, "page_size": 10})
shape("/api/sales/orders", {"page": 1, "page_size": 10})
shape("/api/finance/receivables", {"page": 1, "page_size": 10})