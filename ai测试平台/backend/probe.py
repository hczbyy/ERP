# -*- coding: utf-8 -*-
"""接口契约探测：在生成用例前，用安全请求摸清被测系统的真实返回结构。"""
import re
import time
from typing import Any, Dict, List, Optional

import requests

from . import db


def _sample_query(op: Dict) -> Dict:
    query = {}
    for p in op.get("params") or []:
        if p.get("in") != "query":
            continue
        schema = p.get("schema") or {}
        value = schema.get("example", schema.get("default"))
        if value is None:
            stype = schema.get("type")
            if stype == "integer":
                value = 1
            elif stype == "number":
                value = 1.1
            elif stype == "boolean":
                value = "true"
            else:
                value = "test"
        query[p["name"]] = str(value)
    return query


def _sample_path(op: Dict) -> str:
    path = op.get("path", "")
    for p in op.get("params") or []:
        if p.get("in") != "path":
            continue
        schema = p.get("schema") or {}
        value = schema.get("example", schema.get("default")) or 1
        path = path.replace("{" + p["name"] + "}", str(value))
    return re.sub(r"\{[^}]+\}", "1", path)


def _extract_business_code(body: Any) -> Optional[tuple]:
    if not isinstance(body, dict):
        return None
    for key in ("code", "errcode", "status", "success", "retcode", "resultCode"):
        if key in body and isinstance(body[key], (int, float, str, bool)):
            return key, body[key]
    return None


def probe_operation(op: Dict, env: Dict, settings: Dict) -> Optional[Dict]:
    """探测单个接口（仅 GET/HEAD，安全不产生数据）。"""
    if op.get("method") not in ("GET", "HEAD"):
        return None
    url = str(env.get("base_url") or "").rstrip("/") + _sample_path(op)
    headers = dict(env.get("headers") or {})
    token = (env.get("variables") or {}).get("token")
    if token:
        headers.setdefault("Authorization", f"Bearer {token}")
    query = _sample_query(op)
    try:
        resp = requests.request(
            op["method"],
            url,
            headers=headers,
            params=query,
            timeout=float(settings.get("run_timeout", 30)),
            verify=bool(settings.get("verify_ssl", True)),
        )
    except Exception as exc:  # noqa: BLE001
        return {"probed": False, "error": str(exc)[:200]}
    status = resp.status_code
    try:
        body = resp.json()
    except ValueError:
        body = None
    data = body.get("data") if isinstance(body, dict) else None
    fields: List[str] = []
    data_type = type(data).__name__
    if isinstance(data, dict):
        fields = list(data.keys())[:20]
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        fields = list(data[0].keys())[:20]
    bc = _extract_business_code(body)
    return {
        "probed": True,
        "status": status,
        "business_code": [bc[0], str(bc[1])] if bc else None,
        "data_type": data_type,
        "fields": fields,
        "auth_required": status in (401, 403),
        "sample_text": resp.text[:300],
        "probed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def probe_operations(operation_ids: List[int], env_name: str = "默认环境") -> Dict:
    settings = db.get_settings()
    envs = settings.get("envs") or []
    env = next(
        (e for e in envs if e.get("name") == env_name),
        envs[0] if envs else {},
    )
    ops = db.list_operations()
    by_id = {op["id"]: op for op in ops}
    selected = [by_id[i] for i in operation_ids if i in by_id] or ops
    results = {"probed": 0, "skipped": 0, "failed": 0, "details": []}
    for op in selected:
        contract = probe_operation(op, env, settings)
        if contract is None:
            results["skipped"] += 1
            continue
        if contract.get("probed"):
            results["probed"] += 1
        else:
            results["failed"] += 1
        db.execute(
            "UPDATE api_operations SET contract_json=? WHERE id=?",
            (db.jdumps(contract), op["id"]),
        )
        results["details"].append(
            {"id": op["id"], "name": op["name"], "contract": contract}
        )
    return results
