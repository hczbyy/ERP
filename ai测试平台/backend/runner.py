# -*- coding: utf-8 -*-
"""用例执行引擎：渲染变量、发送请求、执行断言、记录结果。"""
import json
import re
import threading
import time
import traceback
import uuid
from typing import Any, Dict, List, Tuple

import requests

from . import db, reports

VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
MAX_BODY_KEEP = 200000


def render_str(text: str, variables: Dict[str, Any]) -> str:
    if not isinstance(text, str):
        return text

    def repl(match):
        key = match.group(1)
        return str(variables.get(key, match.group(0)))

    return VAR_RE.sub(repl, text)


def _json_path_get(data: Any, path: str):
    if not path:
        return None
    if path.startswith("$."):
        path = path[2:]
    current = data
    for part in re.split(r"\.|\[(\d+)\]", path):
        if part is None or part == "":
            continue
        if part == "length" and isinstance(current, list):
            current = len(current)
            continue
        if isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if 0 <= idx < len(current) else None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _compare(actual: Any, operator: str, expected: str) -> bool:
    if operator == "exists":
        return actual is not None
    if operator == "not_exists":
        return actual is None
    if operator == "is_object":
        return isinstance(actual, dict)
    if operator == "is_array":
        return isinstance(actual, list)
    if operator == "is_string":
        return isinstance(actual, str)
    if operator == "is_number":
        return isinstance(actual, (int, float)) and not isinstance(actual, bool)
    if operator == "is_integer":
        return isinstance(actual, int) and not isinstance(actual, bool)
    if operator == "is_boolean":
        return isinstance(actual, bool)
    if operator == "is_null":
        return actual is None
    if operator == "length":
        try:
            return _compare(len(actual) if actual is not None else 0, "==", str(expected))
        except TypeError:
            return False
    if operator == "contains":
        return str(expected) in ("" if actual is None else str(actual))
    if operator == "not_contains":
        return str(expected) not in ("" if actual is None else str(actual))
    if operator == "regex":
        return re.search(str(expected), "" if actual is None else str(actual)) is not None
    if operator == "type":
        return _type_name(actual) == str(expected)
    if operator in ("==", "!=", ">", ">=", "<", "<="):
        try:
            left = float(actual)
            right = float(expected)
            numeric = True
        except (TypeError, ValueError):
            numeric = False
        if numeric:
            if operator == "==":
                return left == right
            if operator == "!=":
                return left != right
            if operator == ">":
                return left > right
            if operator == ">=":
                return left >= right
            if operator == "<":
                return left < right
            if operator == "<=":
                return left <= right
        left_s, right_s = str(actual), str(expected)
        if operator == "==":
            return left_s == right_s
        if operator == "!=":
            return left_s != right_s
        return False
    return False


def run_assertion(
    assertion: Dict, resp: requests.Response, duration_ms: int, variables: Dict = None
) -> Tuple[bool, str]:
    atype = assertion.get("type", "status_code")
    operator = assertion.get("operator", "==")
    expected = assertion.get("expected", "")
    if variables and isinstance(expected, str):
        expected = render_str(expected, variables)
    if atype == "status_code":
        actual = resp.status_code
        return _compare(actual, operator, str(expected)), str(actual)
    if atype == "time":
        return _compare(duration_ms, operator, str(expected)), f"{duration_ms}ms"
    if atype == "text":
        actual = resp.text
        return _compare(actual, operator, str(expected)), str(actual)[:500]
    if atype == "json":
        try:
            data = resp.json()
        except ValueError:
            return False, "响应不是有效 JSON"
        actual = _json_path_get(data, assertion.get("path", ""))
        expected_raw = str(expected)
        if expected_raw and (
            expected_raw.startswith(("data.", "$."))
            or (expected_raw and expected_raw[0] in "[{")
        ):
            expected_value = _json_path_get(data, expected_raw)
            passed = _compare(actual, operator, expected_value if expected_value is not None else "")
            shown = (
                json.dumps(expected_value, ensure_ascii=False)
                if not isinstance(expected_value, str)
                else expected_value
            )
            return passed, f"{shown}"
        passed = _compare(actual, operator, expected_raw)
        shown = json.dumps(actual, ensure_ascii=False) if not isinstance(actual, str) else actual
        return passed, str(shown)[:500]
    return False, "未知断言类型"


def build_request(case: Dict, env: Dict, settings: Dict, flow_vars: Dict = None) -> Dict:
    variables = dict(env.get("variables") or {})
    if flow_vars:
        variables.update({k: v for k, v in flow_vars.items() if v is not None})
    variables["base_url"] = str(env.get("base_url") or "").rstrip("/")
    variables["timestamp"] = str(int(time.time()))
    variables["uuid"] = uuid.uuid4().hex[:10]

    url = str(case.get("url") or "")
    url = url.replace("{{{", "{{").replace("}}}", "}}")
    path_params = case.get("path_params") or {}
    for key, value in path_params.items():
        variables[key] = render_str(str(value), variables)
    url = render_str(url, variables)
    if url.startswith("/"):
        url = variables["base_url"] + url
    base = variables.get("base_url", "")
    if base and url.startswith(base + "/" + base):
        url = url[len(base) + 1:]

    for key, value in path_params.items():
        rendered = render_str(str(value), variables)
        url = url.replace("{" + key + "}", rendered).replace(":" + key, rendered)

    headers = dict(env.get("headers") or {})
    headers.update(case.get("headers") or {})
    headers = {str(k): render_str(str(v), variables) for k, v in headers.items()}

    query = {str(k): render_str(str(v), variables) for k, v in (case.get("query") or {}).items()}

    body_type = case.get("body_type") or "json"
    body = case.get("body")
    data = None
    if body is not None:
        if body_type == "json":
            if isinstance(body, str):
                body_text = render_str(body, variables)
                try:
                    parsed = json.loads(body_text)
                    body_text = json.dumps(parsed, ensure_ascii=False)
                except ValueError:
                    pass
            else:
                body_text = render_str(json.dumps(body, ensure_ascii=False), variables)
                try:
                    parsed = json.loads(body_text)
                    body_text = json.dumps(parsed, ensure_ascii=False)
                except ValueError:
                    pass
            data = body_text
            headers.setdefault("Content-Type", "application/json")
        elif body_type == "form":
            form = body if isinstance(body, dict) else {}
            data = {str(k): render_str(str(v), variables) for k, v in form.items()}
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            data = render_str(body if isinstance(body, str) else json.dumps(body, ensure_ascii=False), variables)
    return {
        "method": str(case.get("method") or "GET").upper(),
        "url": url,
        "headers": headers,
        "params": query,
        "data": data,
    }


def execute_case(case: Dict, env: Dict, settings: Dict, flow_vars: Dict = None, session: requests.Session = None) -> Dict:
    request_info = build_request(case, env, settings, flow_vars)
    started = time.monotonic()
    try:
        requester = session if session is not None else requests
        resp = requester.request(
            request_info["method"],
            request_info["url"],
            headers=request_info["headers"],
            params=request_info["params"],
            data=request_info["data"],
            timeout=float(settings.get("run_timeout", 30)),
            verify=bool(settings.get("verify_ssl", True)),
            allow_redirects=True,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        response_text = resp.text[:MAX_BODY_KEEP]
        try:
            response_json = resp.json()
        except ValueError:
            response_json = None
        result_items = []
        variables = dict(env.get("variables") or {})
        if flow_vars:
            variables.update({k: v for k, v in flow_vars.items() if v is not None})
        variables["base_url"] = str(env.get("base_url") or "").rstrip("/")
        variables["timestamp"] = str(int(time.time()))
        variables["uuid"] = uuid.uuid4().hex[:10]
        for assertion in case.get("assertions") or []:
            try:
                passed, actual = run_assertion(assertion, resp, duration_ms, variables)
            except Exception as exc:  # noqa: BLE001
                passed, actual = False, f"断言执行异常：{exc}"
            result_items.append(
                {
                    "type": assertion.get("type", "status_code"),
                    "path": assertion.get("path", ""),
                    "operator": assertion.get("operator", "=="),
                    "expected": assertion.get("expected", ""),
                    "actual": actual,
                    "passed": passed,
                }
            )
        status = "passed" if all(r["passed"] for r in result_items) else "failed"
        response_info = {
            "status_code": resp.status_code,
            "elapsed_ms": duration_ms,
            "headers": {k: v for k, v in list(resp.headers.items())[:30]},
            "text": response_text,
            "json": response_json,
        }
        return {
            "status": status,
            "request": request_info,
            "response": response_info,
            "assertions": result_items,
            "error_message": "",
            "duration_ms": duration_ms,
        }
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "status": "error",
            "request": request_info,
            "response": {},
            "assertions": [],
            "error_message": f"{exc}\n{traceback.format_exc(limit=3)}"[:2000],
            "duration_ms": duration_ms,
        }


def _do_run(run_id: int, env_name: str, case_ids: List[int], overrides: Dict = None):
    settings = db.get_settings()
    envs = settings.get("envs") or []
    cases = []
    if case_ids:
        for idx, item in enumerate(case_ids):
            if isinstance(item, dict) and item.get("case"):
                case = dict(item["case"])
                case.setdefault("id", -(idx + 1))
                cases.append(case)
            elif isinstance(item, dict) and item.get("case_id"):
                cid = item["case_id"]
                case = db.get_case(cid)
                if case:
                    if item.get("override"):
                        case.update(item["override"])
                    cases.append(case)
            else:
                cid = item
                case = db.get_case(cid)
                if case:
                    if overrides and cid in overrides:
                        case.update(overrides[cid])
                    cases.append(case)
    else:
        cases = [c for c in db.list_cases() if c["enabled"]]
    if not cases:
        db.execute(
            "UPDATE test_runs SET status='finished', finished_at=datetime('now','localtime'), error=? WHERE id=?",
            (len(cases), run_id),
        )
        return

    db.execute(
        "UPDATE test_runs SET status='running', started_at=datetime('now','localtime') WHERE id=?",
        (run_id,),
    )
    env_map = {e.get("name", "默认环境"): e for e in envs}
    passed = failed = errors = 0
    flow_vars: Dict = {}
    executed: set = set()
    executed_cases: List[Dict] = []
    session = requests.Session()

    def ensure_case(case: Dict, stack: List[int]):
        nonlocal passed, failed, errors
        case_id = case.get("id")
        if case_id in executed:
            return
        setup_id = case.get("setup_case_id")
        if setup_id and setup_id not in executed and setup_id not in stack:
            setup = db.get_case(setup_id)
            if setup:
                ensure_case(setup, stack + [case_id])
        env_name_use = env_name or case.get("env") or "默认环境"
        env = env_map.get(
            env_name_use,
            envs[0]
            if envs
            else {"name": "默认环境", "base_url": "", "headers": {}, "variables": {}},
        )
        result = execute_case(case, env, settings, flow_vars, session)
        status = result["status"]
        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
        else:
            errors += 1
        extracts = {}
        resp_json = result.get("response", {}).get("json")
        resp_text = result.get("response", {}).get("text", "")
        resp_headers = result.get("response", {}).get("headers", {})
        if status != "error":
            for rule in case.get("extract_rules") or []:
                name = (rule.get("name") or "").strip()
                path = (rule.get("path") or "").strip()
                if not name or not path:
                    continue
                source = (rule.get("source") or "json").lower()
                value = None
                if source == "text":
                    match = re.search(path, resp_text)
                    value = match.group(1) if match else None
                elif source == "header":
                    value = resp_headers.get(path)
                elif isinstance(resp_json, dict):
                    value = _json_path_get(resp_json, path)
                if value is not None:
                    flow_vars[name] = value
                    extracts[name] = value
        db.execute(
            """INSERT INTO test_run_items
            (run_id, case_id, case_name, status, request_json, response_json, assertions_json,
             error_message, duration_ms, extracts_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                case_id,
                case.get("name", ""),
                status,
                db.jdumps(result["request"]),
                db.jdumps(result["response"]),
                db.jdumps(result["assertions"]),
                result["error_message"],
                result["duration_ms"],
                db.jdumps(extracts),
            ),
        )
        db.execute(
            "UPDATE test_runs SET total=?, passed=?, failed=?, error=? WHERE id=?",
            (passed + failed + errors, passed, failed, errors, run_id),
        )
        executed.add(case_id)
        executed_cases.append(case)

    for case in cases:
        ensure_case(case, [])

    cleanup_records = []
    if settings.get("auto_cleanup"):
        for case in executed_cases:
            for rule in case.get("cleanup_rules") or []:
                method = str(rule.get("method") or "DELETE").upper()
                url = str(rule.get("url") or "").strip()
                if not url:
                    continue
                env_name_use = env_name or case.get("env") or "默认环境"
                env = env_map.get(
                    env_name_use,
                    envs[0]
                    if envs
                    else {"name": "默认环境", "base_url": "", "headers": {}, "variables": {}},
                )
                variables = dict(env.get("variables") or {})
                variables.update({k: v for k, v in flow_vars.items() if v is not None})
                variables["base_url"] = str(env.get("base_url") or "").rstrip("/")
                variables["timestamp"] = str(int(time.time()))
                variables["uuid"] = uuid.uuid4().hex[:10]
                url = render_str(url.replace("{{{", "{{").replace("}}}", "}}"), variables)
                headers = dict(env.get("headers") or {})
                headers.update(case.get("headers") or {})
                headers = {str(k): render_str(str(v), variables) for k, v in headers.items()}
                record = {
                    "case_name": case.get("name", ""),
                    "method": method,
                    "url": url,
                    "ok": False,
                    "status_code": None,
                    "error": "",
                }
                try:
                    resp = session.request(
                        method,
                        url,
                        headers=headers,
                        timeout=float(settings.get("run_timeout", 30)),
                        verify=bool(settings.get("verify_ssl", True)),
                    )
                    record["status_code"] = resp.status_code
                    record["ok"] = resp.status_code in (200, 201, 202, 204, 404)
                except Exception as exc:  # noqa: BLE001
                    record["error"] = str(exc)[:300]
                cleanup_records.append(record)

    db.execute(
        "UPDATE test_runs SET cleanup_json=? WHERE id=?",
        (db.jdumps(cleanup_records), run_id),
    )

    report_path = reports.generate_report(run_id)
    db.execute(
        "UPDATE test_runs SET status='finished', finished_at=datetime('now','localtime'), passed=?, failed=?, error=?, report_path=? WHERE id=?",
        (passed, failed, errors, report_path, run_id),
    )


def start_run(run_id: int, env_name: str, case_ids: List[int], overrides: Dict = None):
    thread = threading.Thread(
        target=_do_run,
        args=(run_id, env_name, case_ids, overrides),
        daemon=True,
    )
    thread.start()
