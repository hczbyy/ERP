"""认证模块 API：登录 / 当前用户 / 权限 / 修改密码。"""
from api.base import BaseApi


class AuthApi(BaseApi):
    def login(self, body: dict):
        """POST /api/auth/login"""
        return self._post("/api/auth/login", json=body, need_token=False)

    def me(self):
        """GET /api/auth/me"""
        return self._get("/api/auth/me")

    def permissions(self):
        """GET /api/auth/permissions"""
        return self._get("/api/auth/permissions")

    def change_password(self, body: dict):
        """POST /api/auth/change-password"""
        return self._post("/api/auth/change-password", json=body)