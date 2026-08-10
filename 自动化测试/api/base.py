"""API 层基类：统一持有请求客户端，提供四类请求快捷方法。

各模块 API 类继承本类，方法签名与接口一一对应，
返回 requests.Response，由测试层用 common.assertions 断言。
"""
from common.client import RequestClient


class BaseApi:
    def __init__(self, client: RequestClient):
        self._c = client

    def _get(self, path: str, **kwargs):
        return self._c.get(path, **kwargs)

    def _post(self, path: str, **kwargs):
        return self._c.post(path, **kwargs)

    def _put(self, path: str, **kwargs):
        return self._c.put(path, **kwargs)

    def _delete(self, path: str, **kwargs):
        return self._c.delete(path, **kwargs)