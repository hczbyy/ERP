"""pytest 共享夹具：将应用指向临时 SQLite 数据库，保证测试与正式数据隔离。

关键点：必须在导入 app 之前改写 settings.DATABASE_URL，
否则 database.py 会基于正式库创建 engine。
"""
import tempfile
from pathlib import Path

import pytest

_tmpdir = Path(tempfile.mkdtemp(prefix="openerp_test_"))

# ---- 先改配置，再导入应用 ----
import app.config as config  # noqa: E402

config.settings.DATABASE_URL = f"sqlite:///{_tmpdir / 'test_erp.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """每个测试会话共用一个测试库（建表 + 种子数据在 app 导入时完成）。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def api(client):
    """带登录态的 API 辅助对象：get/post/put + 业务码断言。"""

    class Api:
        def __init__(self, username: str, password: str):
            r = client.post("/api/auth/login", json={"username": username, "password": password})
            body = r.json()
            assert body["code"] == 0, body
            self.headers = {"Authorization": f"Bearer {body['data']['token']}"}

        def get(self, path, **params):
            r = client.get(path, headers=self.headers, params=params)
            return self._check(r)

        def post(self, path, body=None):
            r = client.post(path, headers=self.headers, json=body or {})
            return self._check(r)

        def put(self, path, body=None):
            r = client.put(path, headers=self.headers, json=body or {})
            return self._check(r)

        def raw(self, method, path, body=None):
            return client.request(method, path, headers=self.headers, json=body or {})

        @staticmethod
        def _check(r):
            j = r.json()
            assert r.status_code < 400, f"{r.status_code} {j}"
            assert j["code"] == 0, j["message"]
            return j["data"]

    return Api


@pytest.fixture()
def admin(api):
    return api("admin", "admin123")