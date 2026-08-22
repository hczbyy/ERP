# -*- coding: utf-8 -*-
"""AI 接口测试平台 - FastAPI 入口。"""
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, db, importers, probe, runner
from .schemas import AiGenerateIn, CaseIn, RunIn, Settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="AI 接口测试平台", version="1.0.0", lifespan=lifespan)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def stats():
    ops = db.q("SELECT COUNT(*) AS c FROM api_operations", one=True)["c"]
    cases = db.q("SELECT COUNT(*) AS c FROM test_cases", one=True)["c"]
    enabled = db.q("SELECT COUNT(*) AS c FROM test_cases WHERE enabled=1", one=True)["c"]
    runs = db.q("SELECT COUNT(*) AS c FROM test_runs", one=True)["c"]
    last = db.q("SELECT * FROM test_runs ORDER BY id DESC LIMIT 1", one=True)
    recent = db.q("SELECT * FROM test_runs ORDER BY id DESC LIMIT 8")
    last_summary = None
    if last:
        passed = last["passed"] or 0
        total = last["total"] or 0
        last_summary = {
            "id": last["id"],
            "name": last["name"],
            "status": last["status"],
            "total": total,
            "passed": passed,
            "failed": last["failed"] or 0,
            "error": last["error"] or 0,
            "success_rate": round(passed / total * 100, 1) if total else 0,
            "started_at": last["started_at"],
            "report_path": last["report_path"],
        }
    return {
        "operations": ops,
        "cases": cases,
        "enabled_cases": enabled,
        "runs": runs,
        "last_run": last_summary,
        "recent_runs": recent,
    }


@app.get("/api/settings")
def get_settings():
    return db.get_settings()


@app.put("/api/settings")
def put_settings(settings: Settings):
    data = settings.model_dump()
    data["envs"] = [e.model_dump() for e in settings.envs] if isinstance(settings.envs, list) else []
    if not data["envs"]:
        data["envs"] = [{"name": "默认环境", "base_url": "", "headers": {}, "variables": {}}]
    db.save_settings(data)
    return db.get_settings()


class AiTestIn(BaseModel):
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_temperature: float = 0.2
    ai_timeout: int = 120


@app.post("/api/settings/test-ai")
def test_ai(payload: AiTestIn):
    settings = db.get_settings()
    for key in ("ai_base_url", "ai_api_key", "ai_model", "ai_temperature", "ai_timeout"):
        value = getattr(payload, key)
        if value not in ("", None):
            settings[key] = value
    if not settings.get("ai_api_key"):
        raise HTTPException(status_code=400, detail="请先填写 API Key")
    try:
        reply = ai.call_llm("请只回复两个字：正常", settings)
        return {"ok": True, "reply": reply.strip()[:200]}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _save_import(result: dict):
    ops = result.get("operations") or []
    for op in ops:
        db.execute(
            """INSERT INTO api_operations
            (module, name, method, path, description, params_json, body_schema_json,
             body_example_json, response_example_json, security, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                op.get("module", "默认"),
                op.get("name", ""),
                op.get("method", "GET"),
                op.get("path", ""),
                op.get("description", ""),
                db.jdumps(op.get("params", [])),
                db.jdumps(op.get("body_schema")) if op.get("body_schema") is not None else None,
                db.jdumps(op.get("body_example")) if op.get("body_example") is not None else None,
                db.jdumps(op.get("response_example")) if op.get("response_example") is not None else None,
                op.get("security", ""),
                op.get("source", "import"),
            ),
        )
    base_url = result.get("base_url") or ""
    if base_url:
        settings = db.get_settings()
        envs = settings.get("envs") or []
        if envs and not envs[0].get("base_url"):
            envs[0]["base_url"] = base_url
            db.save_settings({"envs": envs})
    modules = sorted({op.get("module", "默认") for op in ops})
    return {"imported": len(ops), "modules": modules, "base_url": base_url, "name": result.get("source_name") or result.get("name", "")}


@app.post("/api/import/file")
async def import_file(file: UploadFile = File(...)):
    content = await file.read()
    try:
        result = importers.parse_import(content, file.filename or "")
    except importers.ImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"解析失败：{exc}") from exc
    return _save_import(result)


class ImportTextIn(BaseModel):
    content: str
    source_name: str = "粘贴的接口文档"


class ProbeIn(BaseModel):
    operation_ids: List[int] = Field(default_factory=list)
    env: str = "默认环境"


@app.post("/api/import/text")
def import_text(payload: ImportTextIn):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="文档内容不能为空")
    try:
        result = importers.parse_import(payload.content, payload.source_name)
    except importers.ImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"解析失败：{exc}") from exc
    return _save_import(result)


@app.get("/api/operations")
def list_operations(search: str = "", module: str = ""):
    return db.list_operations(search, module)


@app.post("/api/operations/probe")
def probe_operations(payload: ProbeIn):
    if not payload.operation_ids:
        return {"probed": 0, "skipped": 0, "failed": 0, "details": [], "message": "请先选择要探测的接口"}
    return probe.probe_operations(payload.operation_ids, payload.env)


@app.get("/api/operations/{operation_id}")
def get_operation(operation_id: int):
    row = db.q("SELECT * FROM api_operations WHERE id = ?", (operation_id,), one=True)
    if not row:
        raise HTTPException(status_code=404, detail="接口不存在")
    return db.row_to_operation(row)


@app.delete("/api/operations/{operation_id}")
def delete_operation(operation_id: int):
    db.execute("DELETE FROM api_operations WHERE id = ?", (operation_id,))
    return {"ok": True}


@app.get("/api/cases")
def list_cases(search: str = "", module: str = "", status: str = ""):
    return db.list_cases(search, module, status)


@app.get("/api/cases/{case_id}")
def get_case(case_id: int):
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    return case


def _case_to_row(case: CaseIn) -> tuple:
    return (
        case.operation_id,
        case.name,
        case.module,
        case.method.upper(),
        case.url,
        case.env,
        db.jdumps(case.headers),
        db.jdumps(case.query),
        db.jdumps(case.path_params),
        db.jdumps(case.body) if case.body is not None else None,
        case.body_type,
        case.expected_status,
        db.jdumps([a.model_dump() for a in case.assertions]),
        case.description,
        case.priority,
        1 if case.enabled else 0,
        case.source,
        case.setup_case_id,
        db.jdumps([r.model_dump() for r in case.extract_rules]),
        db.jdumps([r.model_dump() for r in case.cleanup_rules]),
    )


@app.post("/api/cases")
def create_case(case: CaseIn):
    if not case.name.strip():
        raise HTTPException(status_code=400, detail="用例名称不能为空")
    row = _case_to_row(case)
    new_id = db.execute(
        """INSERT INTO test_cases
        (operation_id, name, module, method, url, env, headers_json, query_json,
         path_params_json, body_json, body_type, expected_status, assertions_json,
         description, priority, enabled, source, setup_case_id, extract_json, cleanup_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        row,
    )
    return db.get_case(new_id)


@app.put("/api/cases/{case_id}")
def update_case(case_id: int, case: CaseIn):
    if not db.get_case(case_id):
        raise HTTPException(status_code=404, detail="用例不存在")
    if not case.name.strip():
        raise HTTPException(status_code=400, detail="用例名称不能为空")
    row = _case_to_row(case) + (case_id,)
    db.execute(
        """UPDATE test_cases SET
        operation_id=?, name=?, module=?, method=?, url=?, env=?, headers_json=?,
        query_json=?, path_params_json=?, body_json=?, body_type=?, expected_status=?,
        assertions_json=?, description=?, priority=?, enabled=?, source=?,
        setup_case_id=?, extract_json=?, cleanup_json=?, updated_at=datetime('now','localtime')
        WHERE id=?""",
        row,
    )
    return db.get_case(case_id)


@app.delete("/api/cases/{case_id}")
def delete_case(case_id: int):
    db.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
    return {"ok": True}


class BatchDeleteIn(BaseModel):
    ids: List[int]


@app.post("/api/cases/batch-delete")
def batch_delete(payload: BatchDeleteIn):
    for cid in payload.ids:
        db.execute("DELETE FROM test_cases WHERE id = ?", (cid,))
    return {"deleted": len(payload.ids)}


@app.post("/api/cases/ai-generate")
def ai_generate(payload: AiGenerateIn):
    try:
        if payload.mode == "free":
            if not payload.free_text.strip():
                raise HTTPException(status_code=400, detail="请填写自然语言需求描述")
            return ai.generate_free_cases(payload.free_text, payload.extra_prompt)
        return ai.generate_cases_for_operations(
            payload.operation_ids, payload.mode, payload.extra_prompt, payload.env
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class FlowStepIn(BaseModel):
    case_id: Optional[int] = None
    override: Optional[Dict] = None
    definition: Optional[Dict] = None


class FlowIn(BaseModel):
    name: str = ""
    description: str = ""
    env: str = "默认环境"
    case_ids: List[Optional[int]] = Field(default_factory=list)
    steps: List[FlowStepIn] = Field(default_factory=list)


def _steps_to_store(payload: FlowIn) -> List[dict]:
    if payload.steps:
        return [
            {"case_id": s.case_id, "override": s.override, "definition": s.definition}
            for s in payload.steps
        ]
    return [{"case_id": cid, "override": None} for cid in payload.case_ids]


def _flow_detail(flow_id: int) -> dict:
    row = db.q("SELECT * FROM business_flows WHERE id = ?", (flow_id,), one=True)
    if not row:
        raise HTTPException(status_code=404, detail="业务流程不存在")
    flow = dict(row)
    ids = db.jloads(flow.pop("case_order_json"), [])
    steps = []
    for item in ids:
        cid = item["case_id"] if isinstance(item, dict) else item
        override = item.get("override") if isinstance(item, dict) else None
        definition = item.get("definition") if isinstance(item, dict) else None
        if definition:
            steps.append(
                {
                    "case_id": None,
                    "name": definition.get("name", "流程内置用例"),
                    "enabled": True,
                    "override": None,
                    "definition": definition,
                }
            )
            continue
        case = db.get_case(cid) if cid else None
        steps.append(
            {
                "case_id": cid,
                "name": case["name"] if case else "（用例已删除）",
                "enabled": bool(case["enabled"]) if case else False,
                "override": override,
            }
        )
    flow["steps"] = steps
    return flow


@app.get("/api/flows")
def list_flows():
    rows = db.q("SELECT * FROM business_flows ORDER BY id DESC")
    result = []
    for row in rows:
        flow = dict(row)
        flow["case_count"] = len(db.jloads(flow.pop("case_order_json"), []))
        result.append(flow)
    return result


@app.post("/api/flows")
def create_flow(payload: FlowIn):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="流程名称不能为空")
    flow_id = db.execute(
        "INSERT INTO business_flows(name, description, env, case_order_json) VALUES (?,?,?,?)",
        (payload.name.strip(), payload.description, payload.env, db.jdumps(_steps_to_store(payload))),
    )
    return _flow_detail(flow_id)


@app.get("/api/flows/{flow_id}")
def get_flow(flow_id: int):
    return _flow_detail(flow_id)


@app.put("/api/flows/{flow_id}")
def update_flow(flow_id: int, payload: FlowIn):
    _flow_detail(flow_id)
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="流程名称不能为空")
    db.execute(
        "UPDATE business_flows SET name=?, description=?, env=?, case_order_json=?, updated_at=datetime('now','localtime') WHERE id=?",
        (payload.name.strip(), payload.description, payload.env, db.jdumps(_steps_to_store(payload)), flow_id),
    )
    return _flow_detail(flow_id)


@app.delete("/api/flows/{flow_id}")
def delete_flow(flow_id: int):
    db.execute("DELETE FROM business_flows WHERE id = ?", (flow_id,))
    return {"ok": True}


@app.post("/api/flows/{flow_id}/run")
def run_flow(flow_id: int):
    flow = _flow_detail(flow_id)
    items = []
    for step in flow["steps"]:
        if step.get("definition"):
            items.append({"case": step["definition"]})
        else:
            items.append({"case_id": step["case_id"], "override": step.get("override")})
    if not items:
        raise HTTPException(status_code=400, detail="流程里还没有用例，请先添加")
    run_id = db.execute(
        "INSERT INTO test_runs(name, status, env, total) VALUES (?, 'running', ?, ?)",
        (f"业务流程：{flow['name']}", flow["env"], len(items)),
    )
    runner.start_run(run_id, flow["env"], items)
    return {"run_id": run_id}


@app.post("/api/runs")
def create_run(payload: RunIn):
    settings = db.get_settings()
    env_name = payload.env or "默认环境"
    if not any(e.get("name") == env_name for e in settings.get("envs", [])):
        env_name = settings["envs"][0]["name"] if settings.get("envs") else "默认环境"
    if payload.case_ids:
        case_ids = payload.case_ids
    else:
        case_ids = [c["id"] for c in db.list_cases() if c["enabled"]]
    if not case_ids:
        raise HTTPException(status_code=400, detail="没有可执行的用例，请先创建或启用用例")
    run_id = db.execute(
        "INSERT INTO test_runs(name, status, env, total) VALUES (?, 'running', ?, ?)",
        (payload.name or f"测试执行 {db.q('SELECT COUNT(*) AS c FROM test_runs', one=True)['c'] + 1}", env_name, len(case_ids)),
    )
    runner.start_run(run_id, env_name, case_ids)
    return {"run_id": run_id}


@app.get("/api/runs")
def list_runs():
    return db.q("SELECT * FROM test_runs ORDER BY id DESC LIMIT 100")


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    run = db.q("SELECT * FROM test_runs WHERE id = ?", (run_id,), one=True)
    if not run:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    run["cleanup"] = db.jloads(run.pop("cleanup_json"), [])
    items = []
    for row in db.q(
        "SELECT i.*, c.module AS module, sc.name AS setup_case_name "
        "FROM test_run_items i "
        "LEFT JOIN test_cases c ON c.id = i.case_id "
        "LEFT JOIN test_cases sc ON sc.id = c.setup_case_id "
        "WHERE i.run_id = ? ORDER BY i.id",
        (run_id,),
    ):
        item = dict(row)
        item["request"] = db.jloads(item.pop("request_json"), {})
        item["response"] = db.jloads(item.pop("response_json"), {})
        item["assertions"] = db.jloads(item.pop("assertions_json"), [])
        item["extracts"] = db.jloads(item.pop("extracts_json"), {})
        items.append(item)
    run["items"] = items
    return run


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: int):
    db.execute("DELETE FROM test_run_items WHERE run_id = ?", (run_id,))
    db.execute("DELETE FROM test_runs WHERE id = ?", (run_id,))
    return {"ok": True}
