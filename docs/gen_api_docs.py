# -*- coding: utf-8 -*-
"""从 FastAPI OpenAPI schema + 路由源码生成中文接口文档。

输出：
  docs/api.md        中文接口文档
  docs/openapi.json  原始 OpenAPI 3.x schema（可导入 Postman/Apifox）
"""
import ast
import inspect
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
DOCS = Path(__file__).resolve().parent

from app.main import app  # noqa: E402

# ---------- 权限提取 ----------


def route_permission(route) -> str | None:
    """从路由依赖中提取 require_permission("xxx") 的权限码。"""
    for dep in route.dependencies:
        fn = getattr(dep, "dependency", None)
        if fn is None or not hasattr(fn, "__closure__"):
            continue
        for cell in fn.__closure__ or []:
            try:
                v = cell.cell_contents
            except ValueError:
                continue
            if isinstance(v, str) and ":" in v and not v.startswith(("http", "Bearer")):
                return v
    return None


# ---------- 响应 data 结构提取（AST） ----------

_MODULE_SRC = {}


def _module_src(module_name: str) -> str:
    if module_name not in _MODULE_SRC:
        try:
            mod = sys.modules[module_name]
            _MODULE_SRC[module_name] = inspect.getsource(mod)
        except (OSError, TypeError):
            _MODULE_SRC[module_name] = ""
    return _MODULE_SRC[module_name]


def _row_keys(module_name: str, fn_name: str) -> list[str] | None:
    """从模块源码中找到 def fn_name 的 return dict 字面量键。"""
    try:
        tree = ast.parse(_module_src(module_name))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            for n in ast.walk(node):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
                    keys = [k.value for k in n.value.keys if isinstance(k, ast.Constant)]
                    if keys:
                        return keys
    return None


def _describe_arg(node, module_name: str):
    """描述 ok(...) 的实参 -> {"paged": bool, "keys": [...]} 或 None。"""
    if isinstance(node, ast.Dict):
        keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
        return {"paged": False, "keys": keys} if keys else None
    if isinstance(node, (ast.List, ast.ListComp, ast.GeneratorExp)):
        elt = node.elt if isinstance(node, ast.ListComp) else node
        if isinstance(elt, ast.Dict):
            keys = [k.value for k in elt.keys if isinstance(k, ast.Constant)]
            return {"paged": False, "keys": keys} if keys else None
        if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name):
            keys = _row_keys(module_name, elt.func.id)
            return {"paged": False, "keys": keys} if keys else None
        return None
    if isinstance(node, ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name == "paginate":
            return {"paged": True, "keys": None}
        if isinstance(func, ast.Name):
            keys = _row_keys(module_name, name)
            return {"paged": False, "keys": keys} if keys else None
        return None
    if isinstance(node, ast.Name):
        # 追踪 handler 内赋值：result = paginate(...) 或 xxx = ok 前文变量
        return {"paged": True, "keys": None} if node.id == "result" else None
    return None


def response_data_desc(route):
    """对 APIRoute 提取响应 data 的结构描述，取不到返回 None。"""
    fn = route.endpoint
    module_name = fn.__module__
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    fns = [n for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn.__name__]
    if not fns:
        return None
    for node in ast.walk(fns[0]):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            func_name = call.func.id if isinstance(call.func, ast.Name) else getattr(call.func, "attr", "")
            if func_name in ("ok", "fail"):
                args = call.args
                if not args:
                    return {"paged": False, "keys": []}
                return _describe_arg(args[0], module_name)
    return None


# ---------- Schema 解析 ----------

_SCHEMAS = {}


def _resolve(ref: str) -> dict:
    return _SCHEMAS.get(ref.split("/")[-1], {})


def param_table(operation: dict) -> str:
    """路径/查询参数 -> Markdown 表格行。"""
    rows = []
    for p in operation.get("parameters", []):
        sch = p.get("schema", {})
        rows.append(f"| {p['name']} | {p['in']} | {sch.get('type', '-')} | "
                    f"{'是' if p.get('required') else '否'} | {p.get('description', '-')} |")
    return "".join(rows)


def body_table(operation: dict) -> tuple[str, str]:
    """请求体 -> (schema 名, Markdown 字段表格)。"""
    rb = operation.get("requestBody")
    if not rb:
        return "", ""
    content = rb.get("content", {}).get("application/json", {})
    ref = content.get("schema", {}).get("$ref", "")
    if not ref:
        return "", ""
    name = ref.split("/")[-1]
    sch = _resolve(ref)
    rows = []
    required = set(sch.get("required", []))
    for fname, fmeta in sch.get("properties", {}).items():
        ftype = fmeta.get("type") or fmeta.get("$ref", "object").split("/")[-1]
        rows.append(f"| {fname} | {ftype} | {'是' if fname in required else '否'} | "
                    f"{fmeta.get('description', '-')} |")
    return name, "".join(rows)


def data_desc_html(desc) -> str:
    if desc is None:
        return "动态结构（运行时确定）"
    if desc.get("paged"):
        return "分页结构：`{ items: [...], total: 总数, page: 当前页, page_size: 每页数量 }`"
    keys = desc.get("keys") or []
    if not keys:
        return "`null`（无数据）"
    return "字段：`" + "`, `".join(keys) + "`"


# ---------- 生成 ----------

def build():
    spec = app.openapi()
    (DOCS / "openapi.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    routes = {f"{r.path}|{r.methods & {'GET','POST','PUT','DELETE','PATCH'}}": r
              for r in app.routes if hasattr(r, "methods")}
    _SCHEMAS.update(spec.get("components", {}).get("schemas", {}))

    # 按 tag 分组
    groups: dict[str, list] = {}
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            key = f"{path}|{method.upper()}"
            route = routes.get(key)
            perm = route_permission(route) if route else None
            desc = response_data_desc(route) if route else None
            body_name, body_rows = body_table(op)
            groups.setdefault((op.get("tags") or ["其他"])[0], []).append({
                "method": method.upper(), "path": path,
                "summary": op.get("summary", ""), "description": (op.get("description") or "").strip(),
                "perm": perm, "params": param_table(op),
                "body_name": body_name, "body_rows": body_rows,
                "data": desc,
            })

    lines = []
    A = lines.append
    A(f"# {spec['info']['title']} API 接口文档")
    A("")
    A(f"> 版本：{spec['info']['version']} ｜ Base URL：`http://127.0.0.1:8000`")
    A(f"> {spec['info']['description']}")
    A("")
    A("## 通用约定")
    A("")
    A("### 认证方式")
    A("")
    A("登录成功后获取 `token`，除登录/健康检查外所有接口需在请求头携带：")
    A("")
    A("```http")
    A("Authorization: Bearer <token>")
    A("```")
    A("")
    A("### 统一响应格式")
    A("")
    A("```json")
    A('{"code": 0, "message": "success", "data": {...}}')
    A("```")
    A("")
    A("| 字段 | 说明 |")
    A("| --- | --- |")
    A("| code | 0 成功；非 0 业务失败（通常 1） |")
    A("| message | 提示信息（业务错误时可直接展示给用户） |")
    A("| data | 业务数据，结构见各接口 |")
    A("")
    A("### 错误状态码")
    A("")
    A("| HTTP 状态码 | 含义 |")
    A("| --- | --- |")
    A("| 400 | 业务规则冲突（库存不足、状态不允许等），响应体为 `{code:1, message, data:null}` |")
    A("| 401 | 未登录 / 凭证无效或过期 |")
    A("| 403 | 无权限（缺少对应权限点） |")
    A("| 500 | 服务器内部错误 |")
    A("")
    A("### 分页参数")
    A("")
    A("列表接口通用查询参数：`page`（页码，默认 1）、`page_size`（每页数量，默认 20）、`keyword`（搜索关键字）。")
    A("")
    A("---")
    A("")
    A("## 接口总览")
    A("")
    A("| 模块 | 方法 | 路径 | 说明 | 权限 |")
    A("| --- | --- | --- | --- | --- |")
    for tag in sorted(groups):
        for op in groups[tag]:
            A(f"| {tag} | {op['method']} | `{op['path']}` | {op['summary']} | "
              f"{op['perm'] or '公开'} |")
    A("")
    A("---")
    A("")

    for tag in sorted(groups):
        A(f"## {tag}")
        A("")
        for op in groups[tag]:
            A(f"### {op['method']} `{op['path']}`")
            A("")
            A(f"**{op['summary'] or '（无描述）'}**")
            A("")
            if op["description"] and op["description"] != op["summary"]:
                A(op["description"].replace("\n", "\n\n"))
                A("")
            A(f"- 权限：`{op['perm']}`" if op["perm"] else "- 权限：公开")
            A(f"- 响应 `data` 结构：{data_desc_html(op['data'])}")
            A("")
            if op["params"]:
                A("**请求参数**")
                A("")
                A("| 名称 | 位置 | 类型 | 必填 | 说明 |")
                A("| --- | --- | --- | --- | --- |")
                A(op["params"])
                A("")
            if op["body_name"]:
                A(f"**请求体（`{op['body_name']}`）**")
                A("")
                A("| 字段 | 类型 | 必填 | 说明 |")
                A("| --- | --- | --- | --- |")
                A(op["body_rows"])
                A("")
        A("---")
        A("")

    (DOCS / "api.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK -> {DOCS / 'api.md'} / {DOCS / 'openapi.json'}")


if __name__ == "__main__":
    build()