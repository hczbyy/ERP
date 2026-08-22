# -*- coding: utf-8 -*-
"""AI 测试用例生成：兼容 OpenAI 接口的大模型 + 无 Key 时的规则模式。"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import requests

from . import db, probe

VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
VALID_PRIORITY = {"P0", "P1", "P2", "P3"}

SYSTEM_PROMPT = (
    "你是一名资深接口测试工程师，擅长从 OpenAPI / Swagger 接口定义中设计高质量的接口测试用例。"
    "你的输出必须严格符合用户要求的 JSON 格式，不能输出 JSON 以外的任何文字。"
    "测试用例要覆盖正常路径、参数校验、边界值、异常场景，并给出字段级断言。"
)

MODE_INSTRUCTIONS = {
    "normal": (
        "生成【正常路径】测试用例：每个接口生成 2~4 条，覆盖成功调用、关键字段存在性/类型断言；"
        "创建类接口断言返回 ID 不为空，查询类接口断言返回列表/关键字段不为空。"
    ),
    "param": (
        "生成【参数校验与异常场景】测试用例：每个接口生成 3~6 条，覆盖必填参数缺失、参数类型错误、"
        "边界值（字符串超长、数字极值）、空值、非法枚举等场景；预期状态码应写 400/404/422/500 等合理值，"
        "断言使用 status_code >= 400 表达异常预期。"
    ),
    "business": (
        "生成【业务场景】测试用例：结合接口依赖关系生成组合用例，例如先登录获取 token，"
        "再携带 Authorization: Bearer {{token}} 调用需要鉴权的接口；每个接口 1~3 条，"
        "跨接口引用使用 {{变量}} 占位。"
    ),
    "all": (
        "综合生成测试用例：正常路径 + 参数校验/边界值 + 业务依赖场景，每个接口生成 5~8 条，"
        "覆盖要全面，断言必须到字段级。"
    ),
}

OUTPUT_FORMAT = """
输出格式（严格 JSON 数组，不要包含任何注释或额外文字）：
[
  {
    "name": "用例名称",
    "module": "所属模块",
    "method": "GET/POST/PUT/DELETE...",
    "url": "{{base_url}}/api/xxx（相对路径必须带 {{base_url}} 前缀）",
    "headers": {"Content-Type": "application/json", "Authorization": "Bearer {{token}}"},
    "query": {"page": "1"},
    "path_params": {"id": "1"},
    "body": {"字段": "值"},
    "body_type": "json/form/raw",
    "expected_status": 200,
    "extract_rules": [
      {"name": "order_id", "path": "data.id", "source": "json"}
    ],
    "setup": {
      "method": "POST",
      "path": "/api/auth/login",
      "extract_rules": [{"name": "token", "path": "data.token"}]
    },
    "cleanup": [
      {"method": "DELETE", "url": "{{base_url}}/api/novels/{{novel_id}}"}
    ],
    "assertions": [
      {"type": "status_code", "operator": "==", "expected": "200"},
      {"type": "json", "path": "code", "operator": "==", "expected": "0"},
      {"type": "json", "path": "data", "operator": "is_object", "expected": ""},
      {"type": "json", "path": "data.list", "operator": "is_array", "expected": ""},
      {"type": "text", "operator": "contains", "expected": "success"},
      {"type": "time", "operator": "<", "expected": "2000"}
    ],
    "description": "用例设计思路说明",
    "priority": "P1"
  }
]

约束：
1. 断言必须到字段级，不能只断 HTTP 状态码；创建类接口必须断言返回 ID 非空（exists 或 != ""）。
2. 接口有鉴权要求时，必须携带 Authorization: Bearer {{token}}，不要写死真实 Token。
3. 需要依赖其他接口返回值时，用 {{变量}} 占位并在 description 中说明依赖关系。
4. 每个用例都必须是可执行的完整请求定义。
5. 业务拒绝类场景（重复数据、状态不允许、记录不存在等）通常返回 HTTP 200 且 code != 0，
   预期应写成 status_code==200 加上 json code != 0，不要直接预期 400/409。
6. 参数类型/必填校验失败时，HTTP 状态码使用 422（除非文档明确写了其他状态码）。
7. 文档没有给出响应字段结构时，禁止编造字段名；只能断言 code 存在、data 存在/类型，或不做字段断言。
8. 鉴权失败用例（无效 Token、未携带 Token）只断言 status_code==401，不要断言 code/message。
9. 路径参数缺失/非法用例不要用空字符串或尾斜杠，用明显非法的值（如 abc、-1），并预期 4xx。
10. JSON 字段断言 operator 只允许：==、!=、>、>=、<、<=、contains、not_contains、exists、
    not_exists、type、regex、is_object、is_array、is_string、is_number、is_integer、is_boolean、is_null。
11. 成功业务码以接口文档为准（常见 0 或 200）；文档写 code=200 时，断言必须写 code==200，不要写 0。
12. 接口依赖：如果本用例需要前置数据（如登录 Token、创建接口返回的 ID），必须给出 setup（前置接口 method + path + extract_rules），
    并在 url/headers/body/path 中用 {{变量}} 引用；创建类接口本用例自身用 extract_rules 提取 ID 供后续用例使用。
    没有依赖的用例 setup 写 null。
13. 禁止写死测试账号、密码、真实 ID 和固定业务数据；请求数据使用接口文档中的示例字段 + {{uuid}} 保证唯一，
    断言完全依据接口文档描述的响应结构制定。
14. 数据清理为可选项：默认不要输出 cleanup；只有明确要求“测试后清理数据”时，
    创建类用例才给出 cleanup 用自己提取的变量删除刚创建的数据，否则 cleanup 一律写 []。
15. 接口定义里带有【实测契约】时，只能断言契约中列出的 data 字段，禁止编造契约外的字段；
    契约显示业务码为某值时（如 code=200），断言必须写 code==200。
    没有实测契约时，按文档描述断言；文档也没给响应结构时，只断言 status 和 code/data 存在。
16. 网页表单系统：请求体用 form（body_type=form）；认证用 Session Cookie（先执行登录接口即可，
    平台会自动保持 Cookie，不要写 Authorization 头）；响应是 HTML 时用 text contains 断言页面提示文字，
    不要断言 JSON 字段；路径参数需要真实 ID 时，extract_rules 用 source=text + 正则路径从页面提取。
"""


def compact_operation(op: Dict) -> Dict:
    params = []
    for p in op.get("params") or []:
        schema = p.get("schema") or {}
        params.append(
            {
                "name": p.get("name", ""),
                "in": p.get("in", "query"),
                "required": bool(p.get("required")),
                "description": p.get("description", ""),
                "type": schema.get("type", ""),
                "format": schema.get("format", ""),
                "enum": schema.get("enum", []),
                "minLength": schema.get("minLength"),
                "maxLength": schema.get("maxLength"),
                "minimum": schema.get("minimum"),
                "maximum": schema.get("maximum"),
            }
        )
    body_schema = op.get("body_schema")
    contract = op.get("contract") or {}
    contract_info = None
    if contract.get("probed"):
        contract_info = {
            "实测HTTP状态码": contract.get("status"),
            "实测业务码": (
                f"{contract['business_code'][0]}={contract['business_code'][1]}"
                if contract.get("business_code")
                else "未发现"
            ),
            "data类型": contract.get("data_type"),
            "data字段": contract.get("fields", []),
            "是否需要鉴权": contract.get("auth_required", False),
        }
    return {
        "接口名称": op.get("name", ""),
        "模块": op.get("module", "默认"),
        "请求方式": op.get("method", "GET"),
        "路径": op.get("path", ""),
        "接口说明": (op.get("description") or "")[:500],
        "鉴权方式": op.get("security", "无"),
        "参数定义": params,
        "请求体Schema": json.dumps(body_schema, ensure_ascii=False)[:3000] if body_schema else None,
        "请求体示例": op.get("body_example"),
        "响应示例": json.dumps(op.get("response_example"), ensure_ascii=False)[:1500]
        if isinstance(op.get("response_example"), (dict, list))
        else op.get("response_example"),
        "实测契约": contract_info,
    }


def build_prompt(op: Dict, mode: str, extra_prompt: str) -> str:
    spec = compact_operation(op)
    prompt = (
        "请基于下面的接口定义生成接口测试用例。\n"
        f"【接口定义】\n{json.dumps(spec, ensure_ascii=False, indent=2)}\n\n"
        f"【任务要求】\n{MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS['all'])}\n"
    )
    if extra_prompt.strip():
        prompt += f"\n【额外要求】\n{extra_prompt.strip()}\n"
    prompt += OUTPUT_FORMAT
    return prompt


def extract_json_array(text: str) -> List[Dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = _repair_repeat_expr(text)
    start = text.find("[")
    if start == -1:
        start = text.find("{")
    if start == -1:
        raise ValueError("AI 返回内容中没有 JSON 数组")
    end = text.rfind("]") if text.find("[") != -1 else text.rfind("}")
    if end < start:
        end = len(text)
    try:
        data = json.loads(text[start : end + 1])
    except ValueError as exc:
        raise ValueError(f"AI 返回的 JSON 无法解析：{exc}") from exc
    if isinstance(data, dict) and isinstance(data.get("cases"), list):
        data = data["cases"]
    if not isinstance(data, list):
        raise ValueError("AI 返回内容不是用例数组")
    return data


def _repair_repeat_expr(text: str) -> str:
    """修复 AI 常见的 `"a".repeat(256)` 之类的非 JSON 表达式。"""

    def repl(match):
        value, count = match.group(1), int(match.group(2))
        return json.dumps(value * min(count, 5000))

    text = re.sub(r'"((?:[^"\\]|\\.)*)"\s*\.\s*repeat\s*\(\s*(\d+)\s*\)', repl, text)
    text = re.sub(r'"((?:[^"\\]|\\.)*)"\s*\*\s*(\d+)', repl, text)
    return text


def call_llm(prompt: str, settings: Dict) -> str:
    if not settings.get("ai_api_key"):
        raise RuntimeError("未配置 AI 模型")
    base_url = str(settings.get("ai_base_url", "")).rstrip("/")
    if not base_url:
        raise RuntimeError("未配置 AI 服务地址")
    url = base_url + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.get("ai_api_key"):
        headers["Authorization"] = f"Bearer {settings['ai_api_key']}"
    payload = {
        "model": settings.get("ai_model", "deepseek-chat"),
        "max_tokens": 8192,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(settings.get("ai_temperature", 0.2)),
        "stream": False,
    }
    resp = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=float(settings.get("ai_timeout", 120)),
    )
    if resp.status_code != 200:
        raise RuntimeError(f"AI 接口调用失败 HTTP {resp.status_code}：{resp.text[:500]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"AI 返回结构异常：{str(data)[:500]}") from exc


def normalize_cases(raw_cases: List[Dict], op: Dict) -> List[Dict]:
    cases = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        method = str(raw.get("method") or op.get("method") or "GET").upper()
        if method not in VALID_METHODS:
            method = "GET"
        url = str(raw.get("url") or "").strip()
        if not url:
            url = f"{{{{base_url}}}}{op.get('path', '')}"
        elif url.startswith("/"):
            url = "{{base_url}}" + url
        elif not url.startswith(("http://", "https://")):
            url = "{{base_url}}/" + url
        while url.startswith("{{base_url}}/{{base_url}}/"):
            url = url.replace("{{base_url}}/{{base_url}}/", "{{base_url}}/", 1)
        module = str(raw.get("module") or op.get("module") or "默认")
        assertions = []
        for a in raw.get("assertions") or []:
            if not isinstance(a, dict):
                continue
            atype = str(a.get("type", "status_code"))
            if atype not in ("status_code", "json", "text", "time"):
                atype = "status_code"
            if atype == "status_code":
                assertions.append(
                    {
                        "type": "status_code",
                        "path": "",
                        "operator": str(a.get("operator") or "=="),
                        "expected": str(a.get("expected") or raw.get("expected_status") or 200),
                    }
                )
            else:
                assertions.append(
                    {
                        "type": atype,
                        "path": str(a.get("path") or ""),
                        "operator": str(a.get("operator") or "=="),
                        "expected": str(a.get("expected") or ""),
                    }
                )
        if not any(a["type"] == "status_code" for a in assertions):
            assertions.insert(
                0,
                {
                    "type": "status_code",
                    "path": "",
                    "operator": "==",
                    "expected": str(raw.get("expected_status") or 200),
                },
            )
        query = raw.get("query") or {}
        headers = raw.get("headers") or {}
        path_params = raw.get("path_params") or {}
        try:
            expected_status = int(raw.get("expected_status") or 200)
        except (TypeError, ValueError):
            expected_status = 200
        priority = str(raw.get("priority") or "P2").upper()
        if priority not in VALID_PRIORITY:
            priority = "P2"
        extract_rules = []
        for rule in raw.get("extract_rules") or []:
            if isinstance(rule, dict) and rule.get("name") and rule.get("path"):
                extract_rules.append(
                    {
                        "name": str(rule["name"]).strip(),
                        "path": str(rule["path"]).strip(),
                        "source": str(rule.get("source") or "json"),
                    }
                )
        setup_spec = raw.get("setup")
        if not isinstance(setup_spec, dict) or not setup_spec.get("method") or not setup_spec.get("path"):
            setup_spec = None
        cleanup_rules = []
        for rule in raw.get("cleanup") or []:
            if isinstance(rule, dict) and rule.get("method") and rule.get("url"):
                cleanup_rules.append(
                    {"method": str(rule["method"]).upper(), "url": str(rule["url"]).strip()}
                )
        cases.append(
            {
                "operation_id": op.get("id"),
                "name": name,
                "module": module,
                "method": method,
                "url": url,
                "env": "默认环境",
                "headers": {str(k): str(v) for k, v in headers.items()},
                "query": {str(k): str(v) for k, v in query.items()},
                "path_params": {str(k): str(v) for k, v in path_params.items()},
                "body": raw.get("body"),
                "body_type": str(raw.get("body_type") or "json"),
                "expected_status": expected_status,
                "assertions": assertions,
                "description": str(raw.get("description") or "")[:1000],
                "priority": priority,
                "enabled": True,
                "source": "ai",
                "extract_rules": extract_rules,
                "setup_spec": setup_spec,
                "cleanup_rules": cleanup_rules,
            }
        )
    return cases


def _mock_sample_query(params: List[Dict]) -> Dict:
    query = {}
    for p in params or []:
        if p.get("in") in ("query", "path") and p.get("required"):
            schema = p.get("schema") or {}
            value = schema.get("example", schema.get("default"))
            if value is None:
                stype = schema.get("type")
                value = 1 if stype == "integer" else 1.1 if stype == "number" else "test"
            query[p["name"]] = str(value)
    return query


def _mock_path_params(op: Dict, query: Dict) -> Dict:
    path_params = {}
    for name in re.findall(r"\{([^}]+)\}", op.get("path") or ""):
        for p in op.get("params") or []:
            if p.get("in") == "path" and p.get("name") == name:
                schema = p.get("schema") or {}
                path_params[name] = str(schema.get("example") or schema.get("default") or "1")
                break
        else:
            path_params[name] = query.pop(name, "1")
    return path_params


def generate_mock_cases(op: Dict, mode: str) -> List[Dict]:
    """无 AI Key 时的规则生成：基于 Schema 的等价类/边界值用例。"""
    cases: List[Dict] = []
    params = op.get("params") or []
    body_schema = op.get("body_schema") or {}
    body_example = op.get("body_example")
    security = op.get("security", "")
    path = op.get("path", "")
    auth_header = {"Authorization": "Bearer {{token}}"} if security else {}
    default_headers = dict(auth_header)
    default_headers.setdefault("Content-Type", "application/json")

    def make(name, desc, query=None, body=None, expected=200, assertions=None, priority="P2", headers=None, path_params=None):
        return {
            "operation_id": op.get("id"),
            "name": name,
            "module": op.get("module", "默认"),
            "method": op.get("method", "GET"),
            "url": "{{base_url}}" + path,
            "env": "默认环境",
            "headers": headers or dict(default_headers),
            "query": query or {},
            "path_params": path_params or {},
            "body": body,
            "body_type": "json",
            "expected_status": expected,
            "assertions": assertions
            or [
                {"type": "status_code", "path": "", "operator": "==", "expected": str(expected)},
                {
                    "type": "json",
                    "path": "code",
                    "operator": "exists",
                    "expected": "",
                },
            ],
            "description": desc,
            "priority": priority,
            "enabled": True,
            "source": "ai",
        }

    query_sample = _mock_sample_query(params)
    path_params = _mock_path_params(op, query_sample)

    if mode in ("normal", "all"):
        assertions = [
            {"type": "status_code", "path": "", "operator": "==", "expected": "200"},
        ]
        resp_ex = op.get("response_example")
        if isinstance(resp_ex, dict) and resp_ex:
            first_key = next(iter(resp_ex))
            assertions.append({"type": "json", "path": first_key, "operator": "exists", "expected": ""})
        cases.append(
            make(
                f"{op.get('name','')} - 正常路径（规则生成）",
                "根据接口定义与示例数据生成的正常调用用例",
                query=query_sample,
                body=body_example if body_example is not None else None,
                expected=200,
                assertions=assertions,
                priority="P1",
                path_params=path_params,
            )
        )

    if mode in ("param", "all"):
        required_query = [p for p in params if p.get("in") == "query" and p.get("required")]
        if required_query:
            missing = dict(query_sample)
            missing.pop(required_query[0]["name"], None)
            cases.append(
                make(
                    f"{op.get('name','')} - 缺少必填参数 {required_query[0]['name']}（规则生成）",
                    "必填查询参数缺失，接口应返回 4xx",
                    query=missing,
                    body=body_example if body_example is not None else None,
                    expected=400,
                    assertions=[
                        {"type": "status_code", "path": "", "operator": ">=", "expected": "400"},
                        {"type": "status_code", "path": "", "operator": "<", "expected": "500"},
                    ],
                    priority="P2",
                    path_params=path_params,
                )
            )
        props = (body_schema or {}).get("properties") or {}
        required_props = [k for k in (body_schema or {}).get("required", []) if k in props]
        if required_props and body_example is not None:
            bad = body_example.copy() if isinstance(body_example, dict) else {}
            bad.pop(required_props[0], None)
            cases.append(
                make(
                    f"{op.get('name','')} - 缺少必填字段 {required_props[0]}（规则生成）",
                    "请求体缺少必填字段，接口应返回 4xx",
                    query=query_sample,
                    body=bad,
                    expected=400,
                    assertions=[
                        {"type": "status_code", "path": "", "operator": ">=", "expected": "400"},
                        {"type": "status_code", "path": "", "operator": "<", "expected": "500"},
                    ],
                    priority="P2",
                    path_params=path_params,
                )
            )
        for prop_name, prop_schema in props.items():
            max_len = prop_schema.get("maxLength")
            if max_len:
                over = {"x" * (int(max_len) + 1)}
                bad_body = body_example.copy() if isinstance(body_example, dict) else {}
                bad_body[prop_name] = "x" * (int(max_len) + 1)
                cases.append(
                    make(
                        f"{op.get('name','')} - {prop_name} 超长边界（规则生成）",
                        f"字段 {prop_name} 超过 maxLength={max_len}，应被拒绝",
                        query=query_sample,
                        body=bad_body,
                        expected=400,
                        assertions=[
                            {"type": "status_code", "path": "", "operator": ">=", "expected": "400"},
                            {"type": "status_code", "path": "", "operator": "<", "expected": "500"},
                        ],
                        priority="P2",
                        path_params=path_params,
                    )
                )
            if prop_schema.get("enum"):
                bad_body = body_example.copy() if isinstance(body_example, dict) else {}
                bad_body[prop_name] = "invalid_enum_value"
                cases.append(
                    make(
                        f"{op.get('name','')} - {prop_name} 非法枚举（规则生成）",
                        f"字段 {prop_name} 传入不在枚举范围内的值",
                        query=query_sample,
                        body=bad_body,
                        expected=400,
                        assertions=[
                            {"type": "status_code", "path": "", "operator": ">=", "expected": "400"},
                            {"type": "status_code", "path": "", "operator": "<", "expected": "500"},
                        ],
                        priority="P2",
                        path_params=path_params,
                    )
                )
            break

    if mode == "business" or (mode == "all" and security):
        auth_case = make(
            f"{op.get('name','')} - 带 Token 鉴权调用（规则生成）",
            "接口声明了鉴权，用例携带 Authorization Bearer Token 占位变量",
            query=query_sample,
            body=body_example if body_example is not None else None,
            expected=200,
            assertions=[
                {"type": "status_code", "path": "", "operator": "==", "expected": "200"},
                {"type": "json", "path": "code", "operator": "exists", "expected": ""},
            ],
            priority="P1",
            headers=dict(auth_header),
            path_params=path_params,
        )
        cases.append(auth_case)
    if op.get("method") == "POST" and cases:
        path_param_names = [p["name"] for p in params if p.get("in") == "path"]
        if path_param_names:
            var = path_param_names[0]
            cases[0]["extract_rules"] = [{"name": var, "path": "data.id"}]
            cases[0]["cleanup_rules"] = [
                {
                    "method": "DELETE",
                    "url": "{{base_url}}"
                    + path.replace("{" + var + "}", "{{" + var + "}}"),
                }
            ]
    return cases


def _norm_path(path: str) -> str:
    path = (path or "").strip()
    for prefix in ("{{base_url}}", "{{ base_url }}"):
        if path.startswith(prefix):
            path = path[len(prefix):]
    return path.rstrip("/")


def _create_setup_case(key: tuple, spec: Dict, templates: Dict, candidate_ops: List[Dict]) -> int | None:
    """根据 AI 给出的前置接口定义，创建/复用一条前置用例（数据来自同批 AI 生成的接口用例）。"""
    method, path = key
    ops = candidate_ops or db.list_operations()
    op = next(
        (o for o in ops if o["method"].upper() == method and _norm_path(o["path"]) == path),
        None,
    )
    if not op and candidate_ops:
        op = next(
            (o for o in db.list_operations() if o["method"].upper() == method and _norm_path(o["path"]) == path),
            None,
        )
    name = f"前置-{method} {path}"
    if op:
        name = f"前置-{op.get('name', '')}"
    existing = db.q(
        "SELECT id FROM test_cases WHERE name=? AND source='ai' LIMIT 1",
        (name,),
        one=True,
    )
    if existing:
        return existing["id"]
    template = templates.get(key)
    if template:
        url, headers, query = template["url"], template["headers"], template["query"]
        path_params, body = template["path_params"], template["body"]
    elif op:
        url, headers, query = "{{base_url}}" + op["path"], {}, {}
        path_params, body = {}, op.get("body_example")
    else:
        return None
    extracts = spec.get("extract_rules") or []
    assertions = [{"type": "status_code", "path": "", "operator": "==", "expected": "200"}]
    for rule in extracts:
        if rule.get("path"):
            assertions.append(
                {"type": "json", "path": rule["path"], "operator": "exists", "expected": ""}
            )
    new_id = db.execute(
        """INSERT INTO test_cases
        (operation_id, name, module, method, url, env, headers_json, query_json,
         path_params_json, body_json, body_type, expected_status, assertions_json,
         description, priority, enabled, source, setup_case_id, extract_json, cleanup_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            op["id"] if op else None,
            name,
            op.get("module", "默认") if op else "默认",
            method,
            url,
            "默认环境",
            db.jdumps(headers),
            db.jdumps(query),
            db.jdumps(path_params),
            db.jdumps(body) if body is not None else None,
            "json",
            200,
            db.jdumps(assertions),
            f"AI 自动创建的前置用例：{method} {path}",
            "P1",
            1,
            "ai",
            None,
            db.jdumps(extracts),
            db.jdumps([]),
        ),
    )
    return new_id


def _resolve_dependencies(cases: List[Dict], candidate_ops: List[Dict] = None) -> List[Dict]:
    """把 AI 输出的 setup 依赖转换为前置用例 ID，并统一保存提取规则。"""
    templates = {}
    for case in cases:
        if case.get("setup_spec"):
            continue
        key = (case["method"].upper(), _norm_path(case.get("url", "")))
        templates.setdefault(key, case)
    setup_cache = {}
    resolved = []
    for case in cases:
        spec = case.get("setup_spec") or {}
        setup_id = None
        if spec:
            key = (str(spec.get("method", "")).upper(), _norm_path(str(spec.get("path", ""))))
            if key in setup_cache:
                setup_id = setup_cache[key]
            else:
                setup_id = _create_setup_case(key, spec, templates, candidate_ops or [])
                setup_cache[key] = setup_id
        case["setup_case_id"] = setup_id
        case["extract_rules"] = case.get("extract_rules") or []
        case["cleanup_rules"] = case.get("cleanup_rules") or []
        case.pop("setup_spec", None)
        resolved.append(case)
    return resolved


def generate_cases_for_operations(
    operation_ids: List[int], mode: str, extra_prompt: str, env_name: str = "默认环境"
) -> Dict:
    settings = db.get_settings()
    ops = db.list_operations()
    by_id = {op["id"]: op for op in ops}
    selected = [by_id[i] for i in operation_ids if i in by_id] or ops
    envs = settings.get("envs") or []
    env = next(
        (e for e in envs if e.get("name") == env_name),
        envs[0] if envs else {},
    )
    # 自动契约探测：仅缺契约的 GET/HEAD 接口，安全不产生数据
    for op in selected:
        if op["method"] in ("GET", "HEAD") and not (op.get("contract") or {}).get("probed"):
            contract = probe.probe_operation(op, env, settings)
            if contract and contract.get("probed"):
                db.execute(
                    "UPDATE api_operations SET contract_json=? WHERE id=?",
                    (db.jdumps(contract), op["id"]),
                )
                op["contract"] = contract
    all_cases: List[Dict] = []
    errors: List[str] = []

    def gen_one(op: Dict):
        if not settings.get("ai_api_key"):
            return generate_mock_cases(op, mode)
        prompt = build_prompt(op, mode, extra_prompt)
        content = call_llm(prompt, settings)
        raw = extract_json_array(content)
        return normalize_cases(raw, op)

    if not settings.get("ai_api_key"):
        for op in selected:
            all_cases.extend(gen_one(op))
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(gen_one, op): op for op in selected}
            for future in futures:
                try:
                    all_cases.extend(future.result())
                except Exception as exc:  # noqa: BLE001
                    op = futures[future]
                    errors.append(f"{op.get('name', '')}: {exc}")

    all_cases = _resolve_dependencies(all_cases, selected)
    saved = 0
    for case in all_cases:
        db.execute(
            """INSERT INTO test_cases
            (operation_id, name, module, method, url, env, headers_json, query_json,
             path_params_json, body_json, body_type, expected_status, assertions_json,
             description, priority, enabled, source, setup_case_id, extract_json, cleanup_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                case["operation_id"],
                case["name"],
                case["module"],
                case["method"],
                case["url"],
                case["env"],
                db.jdumps(case["headers"]),
                db.jdumps(case["query"]),
                db.jdumps(case["path_params"]),
                db.jdumps(case["body"]) if case["body"] is not None else None,
                case["body_type"],
                case["expected_status"],
                db.jdumps(case["assertions"]),
                case["description"],
                case["priority"],
                1 if case["enabled"] else 0,
                case["source"],
                case.get("setup_case_id"),
                db.jdumps(case.get("extract_rules") or []),
                db.jdumps(case.get("cleanup_rules") or []),
            ),
        )
        saved += 1
    return {"generated": len(all_cases), "saved": saved, "errors": errors}


def generate_free_cases(free_text: str, extra_prompt: str = "") -> Dict:
    settings = db.get_settings()
    if not settings.get("ai_api_key"):
        raise RuntimeError("自由描述模式需要先配置 AI 模型")
    prompt = (
        f"请根据下面的自然语言需求生成接口测试用例：\n{free_text}\n"
        + (f"【额外要求】\n{extra_prompt}\n" if extra_prompt.strip() else "")
        + "注意：没有给出明确接口地址时，URL 使用 {{base_url}}/api/xxx 占位。\n"
        + OUTPUT_FORMAT
    )
    content = call_llm(prompt, settings)
    raw = extract_json_array(content)
    cases = normalize_cases(raw, {"id": None, "method": "GET", "path": "/api/xxx", "module": "默认", "name": "自由描述"})
    cases = _resolve_dependencies(cases, [])
    saved = 0
    for case in cases:
        db.execute(
            """INSERT INTO test_cases
            (operation_id, name, module, method, url, env, headers_json, query_json,
             path_params_json, body_json, body_type, expected_status, assertions_json,
             description, priority, enabled, source, setup_case_id, extract_json, cleanup_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                None,
                case["name"],
                case["module"],
                case["method"],
                case["url"],
                case["env"],
                db.jdumps(case["headers"]),
                db.jdumps(case["query"]),
                db.jdumps(case["path_params"]),
                db.jdumps(case["body"]) if case["body"] is not None else None,
                case["body_type"],
                case["expected_status"],
                db.jdumps(case["assertions"]),
                case["description"],
                case["priority"],
                1,
                "ai",
                case.get("setup_case_id"),
                db.jdumps(case.get("extract_rules") or []),
                db.jdumps(case.get("cleanup_rules") or []),
            ),
        )
        saved += 1
    return {"generated": len(cases), "saved": saved, "errors": []}
