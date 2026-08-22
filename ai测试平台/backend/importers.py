# -*- coding: utf-8 -*-
"""接口文档导入：支持 OpenAPI 3.x / Swagger 2.0 / Postman Collection v2.1 / Markdown 接口文档。"""
import json
import re
from typing import Any, Dict, List

import yaml


class ImportError_(Exception):
    pass


def _resolve_refs(obj: Any, root: Dict, depth: int = 0) -> Any:
    """解析 OpenAPI 组件引用 $ref。"""
    if depth > 20:
        return obj
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            key = ref.rsplit("/", 1)[-1]
            target = (
                root.get("components", {}).get("schemas", {}).get(key)
                or root.get("definitions", {}).get(key)
            )
            if target is not None:
                return _resolve_refs(target, root, depth + 1)
        return {k: _resolve_refs(v, root, depth) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_refs(v, root, depth) for v in obj]
    return obj


def _sample_from_schema(schema: Any, depth: int = 0) -> Any:
    """根据 JSON Schema 生成一个可用的示例值。"""
    if not isinstance(schema, dict) or depth > 6:
        return None
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = schema_type[0]
    if schema_type == "object" or "properties" in schema:
        result = {}
        for key, sub in (schema.get("properties") or {}).items():
            result[key] = _sample_from_schema(sub, depth + 1)
        return result
    if schema_type == "array":
        item = _sample_from_schema(schema.get("items", {}), depth + 1)
        return [item] if item is not None else []
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.1
    if schema_type == "boolean":
        return True
    fmt = schema.get("format", "")
    if fmt == "date":
        return "2026-08-11"
    if fmt in ("date-time", "datetime"):
        return "2026-08-11 10:00:00"
    if fmt in ("email",):
        return "test@example.com"
    if fmt in ("uri", "url"):
        return "https://example.com"
    if fmt in ("uuid",):
        return "00000000-0000-0000-0000-000000000000"
    return "test"


def _find_json_schema(obj: Dict) -> Any:
    if not isinstance(obj, dict):
        return None
    if "schema" in obj:
        return obj["schema"]
    if "content" in obj:
        for content in obj["content"].values():
            if "schema" in content:
                return content["schema"]
            if "example" in content:
                return {"example": content["example"]}
    if "example" in obj:
        return {"example": obj["example"]}
    if "examples" in obj and isinstance(obj["examples"], dict):
        for ex in obj["examples"].values():
            if isinstance(ex, dict) and "value" in ex:
                return {"example": ex["value"]}
    return None


def _normalize_operation(op: Dict) -> Dict:
    op.setdefault("module", "默认")
    op.setdefault("name", "")
    op.setdefault("method", "GET")
    op.setdefault("path", "")
    op.setdefault("description", "")
    op.setdefault("params", [])
    op.setdefault("body_schema", None)
    op.setdefault("body_example", None)
    op.setdefault("response_example", None)
    op.setdefault("security", "")
    op.setdefault("source", "import")
    return op


def _security_desc(security_schemes: Dict, security_list: Any) -> str:
    if not isinstance(security_list, list) or not security_list:
        return ""
    descs = []
    for item in security_list[:2]:
        if not isinstance(item, dict):
            continue
        for name, scopes in item.items():
            scheme = (security_schemes or {}).get(name, {})
            stype = scheme.get("type", "")
            if stype == "http":
                descs.append(f"http:{scheme.get('scheme','bearer')}")
            elif stype == "apiKey":
                descs.append(f"apiKey:{scheme.get('in','header')}:{scheme.get('name','X-API-Key')}")
            elif stype == "oauth2":
                descs.append("oauth2")
            else:
                descs.append(name)
    return ",".join(descs)


def parse_openapi(data: Dict) -> Dict:
    is_swagger2 = "swagger" in data
    security_schemes = data.get("components", {}).get("securitySchemes", {}) if not is_swagger2 else data.get("securityDefinitions", {})
    operations: List[Dict] = []
    servers = data.get("servers", []) if not is_swagger2 else []
    base_url = ""
    if servers and isinstance(servers[0], dict):
        base_url = servers[0].get("url", "")
    if is_swagger2:
        base_path = data.get("basePath", "")
        if base_path:
            base_url = (base_url + base_path).rstrip("/")

    paths = data.get("paths", {}) or {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        common_params = path_item.get("parameters", []) or []
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            module = (op.get("tags") or ["默认"])[0]
            name = op.get("summary") or op.get("operationId") or f"{method.upper()} {path}"
            description = op.get("description") or op.get("summary") or ""

            params = []
            for p in (op.get("parameters") or []) + common_params:
                if not isinstance(p, dict):
                    continue
                schema = p.get("schema", {})
                if "content" in p:
                    schema = _find_json_schema(p) or {}
                params.append(
                    {
                        "name": p.get("name", ""),
                        "in": p.get("in", "query"),
                        "required": bool(p.get("required", False)),
                        "description": p.get("description", ""),
                        "schema": schema if isinstance(schema, dict) else {},
                    }
                )

            body_schema = None
            body_example = None
            request_body = op.get("requestBody")
            if isinstance(request_body, dict):
                content = request_body.get("content", {}) or {}
                for ctype in ("application/json", "text/json"):
                    if ctype in content:
                        body_schema = _resolve_refs(_find_json_schema(content[ctype]), data)
                        break
                if body_schema:
                    body_example = _sample_from_schema(body_schema)

            response_example = None
            for status in ("200", "201", "204", "2XX"):
                res = (op.get("responses") or {}).get(status)
                if isinstance(res, dict):
                    schema = _resolve_refs(_find_json_schema(res), data)
                    if schema:
                        response_example = _sample_from_schema(schema) if "example" not in schema else schema["example"]
                    if response_example is not None:
                        break

            security = _security_desc(security_schemes, op.get("security", data.get("security", [])))
            operations.append(
                _normalize_operation(
                    {
                        "module": module,
                        "name": name,
                        "method": method.upper(),
                        "path": path,
                        "description": description,
                        "params": params,
                        "body_schema": body_schema,
                        "body_example": body_example,
                        "response_example": response_example,
                        "security": security,
                        "source": "openapi",
                    }
                )
            )
    return {"name": data.get("info", {}).get("title", "接口文档"), "base_url": base_url, "operations": operations}


def _postman_url(request: Dict) -> str:
    url = request.get("url")
    if isinstance(url, str):
        return url
    if isinstance(url, dict):
        raw = url.get("raw")
        if raw:
            return raw
        parts = []
        if isinstance(url.get("host"), list):
            parts.append(".".join(str(x) for x in url["host"]))
        elif url.get("host"):
            parts.append(str(url["host"]))
        if isinstance(url.get("path"), list):
            parts.append("/".join(str(x) for x in url["path"]))
        elif url.get("path"):
            parts.append(str(url["path"]))
        result = "://".join(parts[:2]) if parts and "://" in parts[0] else "/".join(parts)
        if url.get("query"):
            qs = "&".join(f"{q.get('key','')}={q.get('value','')}" for q in url["query"] if q.get("key"))
            if qs:
                result += ("?" if "?" not in result else "&") + qs
        return result
    return ""


def _postman_base_url(request: Dict) -> str:
    url = request.get("url")
    if isinstance(url, dict):
        protocol = url.get("protocol")
        host = url.get("host")
        if protocol and isinstance(host, list):
            return f"{protocol}://{'.'.join(str(x) for x in host)}"
    raw = _postman_url(request)
    for sep in ("?", "#"):
        if sep in raw:
            raw = raw.split(sep)[0]
    parts = raw.split("/")
    if len(parts) >= 3 and "://" in parts[0]:
        return "//".join(parts[:2])
    return ""


def _md_split_rows(row: str) -> List[List[str]]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [[cell.strip() for cell in part.split("|")] for part in row.split("||") if part.strip()]


def _md_type_schema(stype: str) -> Dict:
    stype = (stype or "").lower()
    mapping = {
        "string": "string",
        "integer": "integer",
        "int": "integer",
        "number": "number",
        "float": "number",
        "decimal": "number",
        "boolean": "boolean",
        "bool": "boolean",
        "array": "array",
        "list": "array",
        "object": "object",
        "json": "object",
        "date": "string",
        "datetime": "string",
    }
    return {"type": mapping.get(stype, "string")}


def parse_markdown(text: str) -> Dict:
    """解析 Markdown 接口文档：支持 `### GET /path` 与 `**POST /path**` 两种格式。"""
    lines = text.splitlines()
    operations: List[Dict] = []
    current_module = "默认"
    base_url = ""
    doc_name = ""
    last_h3 = ""
    perm_map: Dict[tuple, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        m = re.match(r"^#\s+(.+)$", line)
        if m and not line.startswith("##") and not line.startswith("###"):
            doc_name = m.group(1).strip()
            continue
        m = re.search(r"(?:Base URL|服务地址)[：:]\s*`?([^`\s]+)`?", line)
        if m and not base_url:
            base_url = m.group(1).strip().rstrip("/")
            continue
        m = re.match(r"^##\s+(.+)$", line)
        if m and not line.startswith("###"):
            current_module = re.sub(r"^[一二三四五六七八九十]+、\s*", "", m.group(1).strip())
            continue
        if current_module == "接口总览" and line.startswith("|"):
            for cells in _md_split_rows(line):
                if len(cells) >= 4 and cells[0] not in ("模块", ""):
                    methods = cells[1].replace(" ", "").split("/")
                    overview_path = re.sub(r"<([^>]+)>", r"{\1}", cells[2].strip().strip("`"))
                    for met in methods:
                        if met.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                            perm_map[(met.upper(), overview_path)] = cells[3].strip()
            continue
        m = re.match(r"^###\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+`?([^`\s]+)`?\s*$", line, re.IGNORECASE)
        if m:
            method = m.group(1).upper()
            path = m.group(2)
            name = f"{method} {path}"
        else:
            m = re.match(r"^###\s+(.+)$", line)
            if m:
                last_h3 = re.sub(r"^\d+(\.\d+)*\s*", "", m.group(1).strip())
                continue
            m = re.match(
                r"^\*\*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+`?/([^`\s*]+)`?\*\*(.*)$",
                line,
                re.IGNORECASE,
            )
            if m:
                method = m.group(1).upper()
                path = re.sub(r"<([^>]+)>", r"{\1}", "/" + m.group(2))
                name = last_h3 or f"{method} {path}"
            else:
                continue

        perm = perm_map.get((method, path), "")
        security = ""
        if "管理员" in perm:
            security = "cookie:admin"
        elif perm and "公开" not in perm:
            security = "cookie"
        op: Dict = {
            "module": current_module,
            "name": name,
            "method": method,
            "path": path,
            "description": "",
            "params": [],
            "body_schema": None,
            "body_example": None,
            "response_example": None,
            "security": security,
            "source": "markdown",
        }
        desc_lines = []
        section = ""
        params = []
        body_props = []
        body_required = []
        body_name = ""
        while i < len(lines):
            bline = lines[i].strip()
            if bline.startswith("###") or (bline.startswith("##") and not bline.startswith("###")):
                break
            if re.match(r"^\*\*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+`?/", bline, re.IGNORECASE):
                break
            i += 1
            if not bline:
                continue
            if bline.startswith("**请求体"):
                section = "body"
                m_name = re.search(r"请求体（`?([^`）)]+)`?）", bline)
                if m_name:
                    body_name = m_name.group(1)
                continue
            if bline.startswith("**请求参数"):
                section = "params"
                continue
            if bline.startswith("**") and bline.endswith("**") and len(bline) > 4:
                op["name"] = bline.strip("*").strip()
                continue
            if bline.startswith("- 权限"):
                op.setdefault("permission", bline.split("：", 1)[-1].strip() if "：" in bline else bline)
                continue
            if bline.startswith("|"):
                for cells in _md_split_rows(bline):
                    if not cells or all(c in ("", "-", "---", "----") for c in cells):
                        continue
                    first = cells[0].strip()
                    if first == "参数":
                        section = "params" if method == "GET" else "body"
                        continue
                    if first in ("名称", "字段"):
                        continue
                    if section == "params" and len(cells) >= 3:
                        if len(cells) >= 4 and cells[1].lower() in ("query", "path", "header", "body", "form"):
                            params.append(
                                {
                                    "name": cells[0],
                                    "in": cells[1].lower(),
                                    "required": cells[2] == "是" if len(cells) > 2 else False,
                                    "description": cells[4] if len(cells) > 4 else "",
                                    "schema": _md_type_schema(cells[2] if len(cells) > 2 else "string"),
                                }
                            )
                        else:
                            params.append(
                                {
                                    "name": cells[0],
                                    "in": "query",
                                    "required": cells[1] in ("是", "必填"),
                                    "description": cells[2] if len(cells) > 2 else "",
                                    "schema": {"type": "string"},
                                }
                            )
                    elif section == "body" and len(cells) >= 3:
                        if len(cells) >= 4 and cells[1].lower() in (
                            "string", "integer", "number", "boolean", "array", "object", "date"
                        ):
                            field, ftype, required = cells[0], cells[1], (len(cells) > 2 and cells[2] == "是")
                            desc = cells[3] if len(cells) > 3 else ""
                        else:
                            field, ftype, required = cells[0], "string", cells[1] in ("是", "必填")
                            desc = cells[2] if len(cells) > 2 else ""
                        body_props.append(
                            {
                                "name": field,
                                "schema": _md_type_schema(ftype),
                                "required": required,
                                "description": desc,
                            }
                        )
                        if required:
                            body_required.append(field)
                continue
            if bline.startswith(("```", ">", "#")):
                continue
            if bline.startswith("- ") and not bline.startswith("- 权限"):
                desc_lines.append(bline[2:].strip())
            elif not bline.startswith("-"):
                desc_lines.append(bline)
        op["params"] = params
        if body_props:
            properties = {p["name"]: dict(p["schema"]) for p in body_props}
            for p in body_props:
                properties[p["name"]]["description"] = p["description"]
            op["body_schema"] = {"type": "object", "required": body_required, "properties": properties}
            op["body_example"] = _sample_from_schema(op["body_schema"])
            op["body_type_hint"] = "form"
        op["description"] = "；".join(dict.fromkeys(x for x in desc_lines if x))[:1000]
        if "公开" in str(op.get("permission", "")):
            op["security"] = ""
        op.pop("permission", None)
        operations.append(_normalize_operation(op))
    if not operations:
        raise ImportError_("Markdown 文档中没有识别到接口（需要 ### GET /path 这样的格式）")
    return {
        "name": doc_name or "Markdown 接口文档",
        "base_url": base_url,
        "operations": operations,
    }


def parse_postman(data: Dict) -> Dict:
    operations: List[Dict] = []

    def walk(items: List[Dict], parent_module: str = ""):
        for item in items or []:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            module = name if item.get("item") else parent_module or "默认"
            if item.get("item"):
                walk(item["item"], module)
                continue
            request = item.get("request")
            if not isinstance(request, dict):
                continue
            method = (request.get("method") or "GET").upper()
            url = _postman_url(request)
            path = url
            headers = {}
            for h in request.get("header") or []:
                if isinstance(h, dict) and not h.get("disabled"):
                    headers[h.get("key", "")] = h.get("value", "")
            params = []
            url_obj = request.get("url")
            if isinstance(url_obj, dict):
                for qp in url_obj.get("query") or []:
                    if isinstance(qp, dict) and qp.get("key"):
                        params.append(
                            {
                                "name": qp.get("key", ""),
                                "in": "query",
                                "required": False,
                                "description": qp.get("description", ""),
                                "schema": {"type": "string"},
                            }
                        )
            body_example = None
            body = request.get("body")
            if isinstance(body, dict):
                mode = body.get("mode")
                if mode == "raw" and body.get("raw"):
                    try:
                        body_example = json.loads(body["raw"])
                    except (TypeError, ValueError):
                        body_example = body["raw"]
                elif mode in ("urlencoded", "formdata"):
                    body_example = {}
                    for kv in body.get(mode) or []:
                        if isinstance(kv, dict) and kv.get("key") and not kv.get("disabled"):
                            body_example[kv["key"]] = kv.get("value", "")
            response_example = None
            expected_status = 200
            if item.get("response"):
                resp = item["response"][0]
                if isinstance(resp, dict):
                    try:
                        expected_status = int(resp.get("code") or 200)
                    except (TypeError, ValueError):
                        pass
                    if resp.get("body"):
                        try:
                            response_example = json.loads(resp["body"])
                        except (TypeError, ValueError):
                            response_example = resp["body"]
            operations.append(
                _normalize_operation(
                    {
                        "module": module,
                        "name": name or f"{method} {path}",
                        "method": method,
                        "path": path,
                        "description": item.get("description") or "",
                        "params": params,
                        "body_schema": None,
                        "body_example": body_example,
                        "response_example": response_example,
                        "security": "",
                        "source": "postman",
                    }
                )
            )

    walk(data.get("item") or [])
    base_url = ""
    for op in operations:
        candidate = _postman_base_url({"url": op["path"]})
        if candidate:
            base_url = candidate
            break
    return {"name": data.get("info", {}).get("name", "Postman 集合"), "base_url": base_url, "operations": operations}


def parse_import(content: Any, source_name: str = "") -> Dict:
    """content 可以是 bytes / str / dict。"""
    data = content
    if isinstance(content, (bytes, bytearray)):
        text = content.decode("utf-8-sig", errors="replace")
        if text.lstrip().startswith("#") or re.search(
            r"^###\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+", text, re.M | re.IGNORECASE
        ):
            return parse_markdown(text)
        try:
            data = json.loads(text)
        except ValueError:
            try:
                data = yaml.safe_load(text)
            except yaml.YAMLError as exc:
                raise ImportError_(f"文档解析失败：{exc}") from exc
    elif isinstance(content, str):
        stripped = content.lstrip()
        if stripped.startswith("#") or re.search(r"^###\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+", content, re.M | re.IGNORECASE):
            return parse_markdown(content)
        try:
            data = json.loads(content)
        except ValueError:
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as exc:
                raise ImportError_(f"文档解析失败：{exc}") from exc
    if not isinstance(data, dict):
        raise ImportError_("无法识别文档格式，请上传 JSON / YAML 格式的 OpenAPI、Swagger 或 Postman 集合。")
    if "openapi" in data or "swagger" in data:
        result = parse_openapi(data)
    elif "info" in data and "item" in data:
        result = parse_postman(data)
    else:
        raise ImportError_("文档结构无法识别：需要 OpenAPI / Swagger / Postman Collection 格式。")
    if source_name:
        result["source_name"] = source_name
    return result
