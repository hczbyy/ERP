"""系统管理模块测试：用户 / 角色 / 权限 / 部门 / 员工 / 审计日志。"""
import allure
import pytest

from common import data
from common.assertions import (
    assert_success,
    assert_validation_error,
    list_items,
)

pytestmark = allure.feature("系统管理")


# ========== 用户 ==========


@allure.story("用户")
@allure.title("用户创建 → 检索 → 禁用/启用 → 删除")
@allure.severity(allure.severity_level.CRITICAL)
def test_user_crud(system_api):
    body = {
        "username": data.uniq("user"),
        "display_name": data.rand_name("用户"),
        "password": "Test@123456",
        "email": f"{data.uniq('u')}@test.com",
    }
    user = assert_success(system_api.create_user(body))
    user_id = user["id"]

    items = list_items(
        assert_success(system_api.list_users(keyword=body["username"], page=1, page_size=10))
    )
    assert any(str(i.get("id")) == str(user_id) for i in items), "关键字检索未命中新用户"

    # 禁用再启用
    assert_success(system_api.toggle_user_active(user_id))
    assert_success(system_api.toggle_user_active(user_id))

    assert_success(system_api.delete_user(user_id))


@allure.story("用户")
@allure.title("创建用户缺少必填 username 返回参数校验错误")
def test_create_user_missing_username(system_api):
    assert_validation_error(system_api.create_user({"display_name": data.rand_name("用户")}))


# ========== 角色 ==========


@allure.story("角色")
@allure.title("角色创建 → 更新 → 删除")
@allure.severity(allure.severity_level.CRITICAL)
def test_role_crud(system_api):
    body = {"code": data.uniq("ROLE"), "name": data.rand_name("角色")}
    role = assert_success(system_api.create_role(body))
    role_id = role["id"]

    assert_success(system_api.update_role(role_id, {**body, "name": data.rand_name("角色改")}))
    assert_success(system_api.delete_role(role_id))


@allure.story("角色")
@allure.title("查询全部权限点成功")
def test_permissions_list(system_api):
    data_ = assert_success(system_api.list_permissions())
    assert data_ is not None, "权限点返回为空"


# ========== 部门 ==========


@allure.story("部门")
@allure.title("部门创建 → 更新 → 删除")
@allure.severity(allure.severity_level.CRITICAL)
def test_department_crud(system_api):
    body = {"code": data.uniq("DEPT"), "name": data.rand_name("部门")}
    dept = assert_success(system_api.create_department(body))
    dept_id = dept["id"]

    assert list_items(assert_success(system_api.list_departments()))
    assert_success(system_api.update_department(dept_id, {**body, "name": data.rand_name("部门改")}))
    assert_success(system_api.delete_department(dept_id))


# ========== 员工 ==========


@allure.story("员工")
@allure.title("员工创建 → 检索 → 更新 → 删除")
@allure.severity(allure.severity_level.CRITICAL)
def test_employee_crud(system_api, department):
    body = {
        "emp_no": data.uniq("EMP"),
        "name": data.rand_name("员工"),
        "phone": data.rand_phone(),
        "status": "active",
        "department_id": department,
    }
    emp = assert_success(system_api.create_employee(body))
    emp_id = emp["id"]

    items = list_items(
        assert_success(system_api.list_employees(keyword=body["name"], page=1, page_size=10))
    )
    assert any(str(i.get("id")) == str(emp_id) for i in items), "关键字检索未命中新员工"

    assert_success(system_api.update_employee(emp_id, {**body, "name": data.rand_name("员工改")}))
    assert_success(system_api.delete_employee(emp_id))


# ========== 审计日志 ==========


@allure.story("审计日志")
@allure.title("分页查询审计日志成功")
def test_audit_logs_list(system_api):
    assert_success(system_api.list_audit_logs(page=1, page_size=10))