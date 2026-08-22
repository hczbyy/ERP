# -*- coding: utf-8 -*-
"""SQLite 数据访问层，所有数据保存在平台目录下的 data/app.db。"""
import json
import os
import sqlite3
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT DEFAULT '默认',
    name TEXT DEFAULT '',
    method TEXT DEFAULT 'GET',
    path TEXT DEFAULT '',
    description TEXT DEFAULT '',
    params_json TEXT DEFAULT '[]',
    body_schema_json TEXT,
    body_example_json TEXT,
    response_example_json TEXT,
    security TEXT DEFAULT '',
    source TEXT DEFAULT 'import',
    contract_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER,
    name TEXT DEFAULT '',
    module TEXT DEFAULT '默认',
    method TEXT DEFAULT 'GET',
    url TEXT DEFAULT '',
    env TEXT DEFAULT '默认环境',
    headers_json TEXT DEFAULT '{}',
    query_json TEXT DEFAULT '{}',
    path_params_json TEXT DEFAULT '{}',
    body_json TEXT,
    body_type TEXT DEFAULT 'json',
    expected_status INTEGER DEFAULT 200,
    assertions_json TEXT DEFAULT '[]',
    description TEXT DEFAULT '',
    priority TEXT DEFAULT 'P2',
    enabled INTEGER DEFAULT 1,
    source TEXT DEFAULT 'manual',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    setup_case_id INTEGER,
    extract_json TEXT DEFAULT '[]',
    cleanup_json TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '',
    status TEXT DEFAULT 'running',
    env TEXT DEFAULT '默认环境',
    total INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    error INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    report_path TEXT DEFAULT '',
    cleanup_json TEXT DEFAULT '[]',
    started_at TEXT DEFAULT (datetime('now','localtime')),
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS test_run_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    case_id INTEGER,
    case_name TEXT DEFAULT '',
    status TEXT DEFAULT 'running',
    request_json TEXT DEFAULT '{}',
    response_json TEXT DEFAULT '{}',
    assertions_json TEXT DEFAULT '[]',
    error_message TEXT DEFAULT '',
    duration_ms INTEGER DEFAULT 0,
    extracts_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS business_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    env TEXT DEFAULT '默认环境',
    case_order_json TEXT DEFAULT '[]',
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

DEFAULT_SETTINGS = {
    "ai_base_url": "https://api.deepseek.com/v1",
    "ai_api_key": "",
    "ai_model": "deepseek-chat",
    "ai_temperature": 0.2,
    "ai_timeout": 120,
    "mock_mode": True,
    "run_timeout": 30,
    "verify_ssl": True,
    "auto_cleanup": False,
    "envs": [
        {
            "name": "默认环境",
            "base_url": "",
            "headers": {},
            "variables": {},
        }
    ],
}


def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with _lock:
        conn = get_conn()
        try:
            conn.executescript(SCHEMA)
            test_case_cols = {r["name"] for r in conn.execute("PRAGMA table_info(test_cases)")}
            if "setup_case_id" not in test_case_cols:
                conn.execute("ALTER TABLE test_cases ADD COLUMN setup_case_id INTEGER")
            if "extract_json" not in test_case_cols:
                conn.execute("ALTER TABLE test_cases ADD COLUMN extract_json TEXT DEFAULT '[]'")
            if "cleanup_json" not in test_case_cols:
                conn.execute("ALTER TABLE test_cases ADD COLUMN cleanup_json TEXT DEFAULT '[]'")
            op_cols = {r["name"] for r in conn.execute("PRAGMA table_info(api_operations)")}
            if "contract_json" not in op_cols:
                conn.execute("ALTER TABLE api_operations ADD COLUMN contract_json TEXT DEFAULT '{}'")
            run_cols = {r["name"] for r in conn.execute("PRAGMA table_info(test_runs)")}
            if "cleanup_json" not in run_cols:
                conn.execute("ALTER TABLE test_runs ADD COLUMN cleanup_json TEXT DEFAULT '[]'")
            item_cols = {r["name"] for r in conn.execute("PRAGMA table_info(test_run_items)")}
            if "extracts_json" not in item_cols:
                conn.execute("ALTER TABLE test_run_items ADD COLUMN extracts_json TEXT DEFAULT '{}'")
            existing = {r["key"] for r in conn.execute("SELECT key FROM settings")}
            for key, value in DEFAULT_SETTINGS.items():
                if key not in existing:
                    conn.execute(
                        "INSERT INTO settings(key, value) VALUES(?, ?)",
                        (key, json.dumps(value, ensure_ascii=False)),
                    )
            conn.commit()
        finally:
            conn.close()


def q(sql, params=(), one=False):
    """查询，返回 dict 列表或单个 dict。"""
    with _lock:
        conn = get_conn()
        try:
            rows = conn.execute(sql, params).fetchall()
            result = [dict(r) for r in rows]
            return (result[0] if result else None) if one else result
        finally:
            conn.close()


def execute(sql, params=()):
    """写操作，返回 lastrowid。"""
    with _lock:
        conn = get_conn()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def executemany(sql, seq_params):
    with _lock:
        conn = get_conn()
        try:
            conn.executemany(sql, seq_params)
            conn.commit()
        finally:
            conn.close()


def jloads(text, default=None):
    if text in (None, ""):
        return default if default is not None else ({} if default is None else default)
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default if default is not None else {}


def jdumps(obj):
    return json.dumps(obj, ensure_ascii=False, default=str)


def get_settings() -> dict:
    rows = q("SELECT key, value FROM settings")
    result = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except (TypeError, ValueError):
            result[row["key"]] = row["value"]
    for key, default in DEFAULT_SETTINGS.items():
        result.setdefault(key, default)
    return result


def save_settings(settings: dict):
    for key, value in settings.items():
        if key in DEFAULT_SETTINGS:
            execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )


def row_to_case(row) -> dict:
    case = dict(row)
    case["headers"] = jloads(case.pop("headers_json"))
    case["query"] = jloads(case.pop("query_json"))
    case["path_params"] = jloads(case.pop("path_params_json"))
    case["body"] = jloads(case.pop("body_json"), None)
    case["assertions"] = jloads(case.pop("assertions_json"), [])
    case["extract_rules"] = jloads(case.pop("extract_json"), [])
    case["cleanup_rules"] = jloads(case.pop("cleanup_json"), [])
    case["enabled"] = bool(case["enabled"])
    return case


def row_to_operation(row) -> dict:
    op = dict(row)
    op["params"] = jloads(op.pop("params_json"), [])
    op["body_schema"] = jloads(op.pop("body_schema_json"), None)
    op["body_example"] = jloads(op.pop("body_example_json"), None)
    op["response_example"] = jloads(op.pop("response_example_json"), None)
    op["contract"] = jloads(op.pop("contract_json"), {})
    return op


def list_cases(search="", module="", status=""):
    sql = "SELECT * FROM test_cases WHERE 1=1"
    params = []
    if search:
        sql += " AND (name LIKE ? OR url LIKE ? OR description LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]
    if module:
        sql += " AND module = ?"
        params.append(module)
    if status == "enabled":
        sql += " AND enabled = 1"
    elif status == "disabled":
        sql += " AND enabled = 0"
    sql += " ORDER BY id DESC"
    return [row_to_case(r) for r in q(sql, params)]


def get_case(case_id):
    row = q("SELECT * FROM test_cases WHERE id = ?", (case_id,), one=True)
    return row_to_case(row) if row else None


def list_operations(search="", module=""):
    sql = "SELECT * FROM api_operations WHERE 1=1"
    params = []
    if search:
        sql += " AND (name LIKE ? OR path LIKE ? OR description LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]
    if module:
        sql += " AND module = ?"
        params.append(module)
    sql += " ORDER BY id DESC"
    return [row_to_operation(r) for r in q(sql, params)]
