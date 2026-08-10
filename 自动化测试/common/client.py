"""HTTP 请求客户端：统一鉴权、超时、日志与 401 自动重登。

- 登录后自动携带 `Authorization: Bearer <token>`；
- 响应 401 时自动重新登录并重试一次（幂等操作安全）；
- 每次请求输出方法、URL、耗时与状态码，便于定位问题。
"""
import time

import requests

from common import config
from common.logger import logger


class RequestClient:
    """封装 requests.Session 的薄客户端，所有 API 对象共享同一实例。"""

    def __init__(
        self,
        base_url: str = config.BASE_URL,
        username: str = config.ADMIN_USERNAME,
        password: str = config.ADMIN_PASSWORD,
        timeout: int = config.TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.token: str | None = None

    # ---------- 鉴权 ----------

    def login(self) -> str:
        """调用登录接口获取 token。兼容 data.token / data.access_token 两种结构。"""
        resp = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"登录失败 HTTP {resp.status_code}: {resp.text[:300]}")
        body = resp.json()
        if body.get("code") != 0:
            raise RuntimeError(f"登录失败: {body.get('message')}")
        data = body.get("data") or {}
        token = data.get("token") or data.get("access_token")
        if not token:
            raise RuntimeError(f"登录响应中未找到 token: {body}")
        self.token = token
        logger.info("登录成功: %s", self.username)
        return token

    def is_logged_in(self) -> bool:
        return bool(self.token)

    # ---------- 请求 ----------

    def request(
        self,
        method: str,
        path: str,
        *,
        need_token: bool = True,
        retry_on_401: bool = True,
        **kwargs,
    ) -> requests.Response:
        """发送请求。

        :param need_token: 是否携带 Bearer token（login/health 等公开接口传 False）
        :param retry_on_401: token 失效时自动重新登录重试一次
        """
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        headers = dict(kwargs.pop("headers", None) or {})
        if need_token and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        start = time.perf_counter()
        resp = self.session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
        cost = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %s (%.0fms)", method.upper(), url, resp.status_code, cost)

        if resp.status_code == 401 and need_token and retry_on_401 and self.token:
            logger.warning("token 失效(401)，重新登录后重试: %s %s", method.upper(), url)
            self.login()
            return self.request(method, path, need_token=need_token, retry_on_401=False, **kwargs)
        return resp

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)