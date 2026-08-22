# -*- coding: utf-8 -*-
"""测试报告生成：使用 Jinja2 模板输出可独立打开的 HTML 报告。"""
import json
import os
import time
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _fmt_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms} ms"
    return f"{ms / 1000:.2f} s"


def _param_rows(req: dict) -> list:
    rows = []
    for key, value in (req.get("params") or {}).items():
        rows.append(("查询参数", key, value))
    for key, value in (req.get("headers") or {}).items():
        rows.append(("请求头", key, value))
    data = req.get("data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            pass
    if isinstance(data, dict):
        for key, value in data.items():
            shown = value if not isinstance(value, (dict, list)) else json.dumps(value, ensure_ascii=False)
            rows.append(("请求体", key, shown))
    elif data not in (None, ""):
        rows.append(("请求体", "(原始)", str(data)[:500]))
    return rows


def _summary(run: Dict, items: list) -> Dict:
    total = len(items)
    passed = sum(1 for i in items if i["status"] == "passed")
    failed = sum(1 for i in items if i["status"] == "failed")
    errors = sum(1 for i in items if i["status"] == "error")
    success_rate = (passed / total * 100) if total else 0
    duration_ms = run.get("duration_ms") or (max((i["duration_ms"] or 0) for i in items) if items else 0)
    modules = {}
    for item in items:
        mod = item.get("module") or "未分类"
        entry = modules.setdefault(
            mod,
            {"name": mod, "total": 0, "passed": 0, "failed": 0, "errors": 0, "success_rate": 0},
        )
        entry["total"] += 1
        if item["status"] == "passed":
            entry["passed"] += 1
        elif item["status"] == "failed":
            entry["failed"] += 1
        else:
            entry["errors"] += 1
    for entry in modules.values():
        entry["success_rate"] = round(entry["passed"] / entry["total"] * 100, 1) if entry["total"] else 0
    module_list = sorted(modules.values(), key=lambda m: (-m["total"], m["name"]))
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "success_rate": round(success_rate, 1),
        "modules": module_list,
        "cleanup": db.jloads(run.get("cleanup_json"), []),
        "duration": _fmt_duration(duration_ms),
        "name": run.get("name") or f"测试执行 #{run['id']}",
        "env": run.get("env", ""),
        "started_at": run.get("started_at", ""),
        "finished_at": run.get("finished_at", ""),
    }


def generate_report(run_id: int) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    run = db.q("SELECT * FROM test_runs WHERE id = ?", (run_id,), one=True)
    rows = db.q(
        "SELECT i.*, c.module AS module, sc.name AS setup_case_name "
        "FROM test_run_items i "
        "LEFT JOIN test_cases c ON c.id = i.case_id "
        "LEFT JOIN test_cases sc ON sc.id = c.setup_case_id "
        "WHERE i.run_id = ? ORDER BY i.id",
        (run_id,),
    )
    items = []
    for row in rows:
        item = dict(row)
        item["request"] = db.jloads(item.pop("request_json"), {})
        item["response"] = db.jloads(item.pop("response_json"), {})
        item["assertions"] = db.jloads(item.pop("assertions_json"), [])
        item["extracts"] = db.jloads(item.pop("extracts_json"), {})
        item["param_rows"] = _param_rows(item["request"])
        item["duration_text"] = _fmt_duration(item.get("duration_ms") or 0)
        items.append(item)
    summary = _summary(run, items)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html")
    html = template.render(summary=summary, items=items, generated_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    filename = f"report_{run_id}.html"
    path = os.path.join(REPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return filename
