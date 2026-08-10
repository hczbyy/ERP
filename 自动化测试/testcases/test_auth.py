"""认证模块测试：登录、当前用户、权限、修改密码。"""
import allure
import pytest

from common import data
from common.assertions import (
    assert_business_error,
    assert_success,
    assert_unauthorized,
)

pytestmark = allure.feature("认证")

_WRONG_PASSWORD = "wrong-password-123"


@allure.story("登录")
@allure.title("正确账号密码登录成功，返回 token")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_success(fresh_client, auth_config):
    resp = fresh_client.post(
        "/api/auth/login",
        json={"username": auth_config["username"], "password": auth_config["password"]},
        need_token=False,
    )
    token = assert_success(resp)
    assert token.get("token") or token.get("access_token"), f"登录响应缺少 token: {token}"


@allure.story("登录")
@allure.title("错误密码登录失败，返回业务错误")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_wrong_password(fresh_client, auth_config):
    # 实际后端返回 200 + code:1（用户名或密码错误），而非 401
    resp = fresh_client.post(
        "/api/auth/login",
        json={"username": auth_config["username"], "password": _WRONG_PASSWORD},
        need_token=False,
    )
    assert_business_error(resp, http_status=200)


@allure.story("登录")
@allure.title("缺失密码字段登录失败，返回参数校验错误")
def test_login_missing_password(fresh_client, auth_config):
    resp = fresh_client.post(
        "/api/auth/login",
        json={"username": auth_config["username"]},
        need_token=False,
    )
    assert resp.status_code == 422, f"期望 422，实际 {resp.status_code}"


@allure.story("当前用户")
@allure.title("未携带 token 访问 /me 返回 401")
@allure.severity(allure.severity_level.CRITICAL)
def test_me_unauthorized(fresh_client):
    assert_unauthorized(fresh_client.get("/api/auth/me"))


@allure.story("当前用户")
@allure.title("携带 token 获取当前用户信息成功")
def test_me_success(auth_api):
    data_ = assert_success(auth_api.me())
    assert data_, "me 返回空数据"


@allure.story("权限")
@allure.title("获取当前用户权限点成功")
def test_permissions_success(auth_api):
    data_ = assert_success(auth_api.permissions())
    assert data_ is not None


@allure.story("修改密码")
@allure.title("旧密码错误时修改密码失败，返回业务错误")
def test_change_password_wrong_old(auth_api, auth_config):
    # 实际后端返回 200 + code:1（原密码不正确），而非 400
    resp = auth_api.change_password(
        {"old_password": _WRONG_PASSWORD, "new_password": data.uniq("Pwd")}
    )
    assert_business_error(resp, http_status=200)


@allure.story("修改密码")
@allure.title("修改密码后可用新密码登录，并恢复原密码")
@allure.severity(allure.severity_level.CRITICAL)
def test_change_password_flow(auth_api, fresh_client, auth_config):
    old, new = auth_config["password"], data.uniq("Pwd")
    try:
        assert_success(auth_api.change_password({"old_password": old, "new_password": new}))
        resp = fresh_client.post(
            "/api/auth/login", json={"username": auth_config["username"], "password": new}
        )
        assert_success(resp)
    finally:
        # 无论用例结果如何都恢复原密码，避免影响后续用例
        assert_success(auth_api.change_password({"old_password": new, "new_password": old}))