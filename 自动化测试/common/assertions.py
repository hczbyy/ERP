"""响应断言工具。

统一响应格式：{"code": 0, "message": "success", "data": ...}
  - code == 0      业务成功
  - code == 1      业务失败（HTTP 通常 400，如库存不足、状态不允许）
  - HTTP 401       未登录 / 凭证无效
  - HTTP 403       无权限
  - HTTP 404       资源不存在
"""
import requests


def _json(resp: requests.Response) -> dict:
    """兼容空响应体，出错时给出可读信息。"""
    try:
        return resp.json()
    except ValueError:
        raise AssertionError(f"响应不是合法 JSON: status={resp.status_code} body={resp.text[:500]}")


def assert_success(resp: requests.Response, http_status: int = 200) -> dict:
    """断言 HTTP 状态码与业务 code==0，返回 data。"""
    assert resp.status_code == http_status, (
        f"期望 HTTP {http_status}，实际 {resp.status_code}，body={resp.text[:500]}"
    )
    body = _json(resp)
    assert body.get("code") == 0, f"业务失败: code={body.get('code')} message={body.get('message')}"
    return body.get("data")


def assert_business_error(resp: requests.Response, http_status: int = 400) -> dict:
    """断言业务失败（code==1，如库存不足/状态不允许/参数冲突）。"""
    assert resp.status_code == http_status, (
        f"期望 HTTP {http_status}，实际 {resp.status_code}，body={resp.text[:500]}"
    )
    body = _json(resp)
    assert body.get("code") != 0, f"期望业务失败但成功: {body}"
    return body


def assert_unauthorized(resp: requests.Response) -> dict:
    """断言未登录/凭证无效（401）。"""
    assert resp.status_code == 401, f"期望 401，实际 {resp.status_code}，body={resp.text[:500]}"
    return _json(resp)


def assert_not_found(resp: requests.Response) -> dict:
    """断言资源不存在（404）。"""
    assert resp.status_code == 404, f"期望 404，实际 {resp.status_code}，body={resp.text[:500]}"
    return _json(resp)


def assert_validation_error(resp: requests.Response) -> dict:
    """断言参数校验失败（422：必填缺失、类型错误）。"""
    assert resp.status_code == 422, f"期望 422，实际 {resp.status_code}，body={resp.text[:500]}"
    return _json(resp)


def list_items(data) -> list:
    """兼容两种分页结构：data 直接为数组，或 data 含 items/records 字段。"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "records", "list"):
            if key in data:
                return data[key] or []
    return []